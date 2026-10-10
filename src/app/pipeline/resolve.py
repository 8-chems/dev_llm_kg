from typing import Any
from pydantic import BaseModel
from src.app.models.decisions import Candidate, JevDecision
from src.app.clients.graph import GraphClient
from src.app.clients.jev import JevClient
from src.app.pipeline.gate import gate
from src.app.safety.untrusted import untrusted, UNTRUSTED_HEADER_INSTRUCTION


class ChoiceQuestionMock:

    def __init__(self, instructions: str, criteria: dict[str, str]):
        self.instructions = instructions
        self.criteria = criteria


def build_resolve_question(cands: list[Candidate]) -> Any:
    criteria = {
        c.cid: f"{c.name} ({', '.join(c.labels)}): {c.summary[:160]}"
        for c in cands
    }
    criteria["none"] = "None of these candidates is the entity the user means"
    instructions = (
        f"{UNTRUSTED_HEADER_INSTRUCTION} "
        "Pick the candidate that is the entity the user's mention refers to. "
        "If unsure or no candidate fits, answer none."
    )

    try:
        from typesafe_sdk import Choice

        return Choice(instructions=instructions, criteria=criteria)
    except Exception:
        return ChoiceQuestionMock(instructions=instructions, criteria=criteria)


class ResolveResult(BaseModel):
    candidate: Candidate | None = None
    decision: JevDecision
    escalate: bool = False
    candidates: list[Candidate] = []


async def resolve(
    mention: str,
    question: str,
    graph: GraphClient,
    jev: JevClient,
    taus: dict[str, float],
    cap: int = 50,
) -> ResolveResult:
    # 1. Query candidates from Neo4j fulltext index
    raw_nodes = await graph.search_candidates(mention, cap=cap)
    if not raw_nodes:
        fallback_decision = JevDecision(
            name="resolve",
            choice="none",
            p=1.0,
            probs={"none": 1.0},
            model_version="code-fallback",
            latency_ms=0,
        )
        return ResolveResult(
            candidate=None, decision=fallback_decision, escalate=True
        )

    # 2. Map candidates to opaque IDs
    candidates = [
        Candidate(
            cid=f"c{idx}",
            node_id=n.node_id,
            name=n.name,
            labels=n.labels,
            summary=n.summary,
        )
        for idx, n in enumerate(raw_nodes)
    ]

    # 3. Construct Jev state and question
    state = {
        "question": untrusted(question),
        "entity_mention": untrusted(mention),
        "candidates": [
            untrusted(
                {
                    "cid": c.cid,
                    "name": c.name,
                    "labels": c.labels,
                    "summary": c.summary,
                }
            )
            for c in candidates
        ],
    }

    q_obj = build_resolve_question(candidates)

    # 4. Call Jev
    r, ms = await jev.decide(state, {"resolve": q_obj})

    choice_res = r.choices.get("resolve") if hasattr(r, "choices") else None
    if choice_res:
        pick = getattr(choice_res, "choice", "none")
        probs = getattr(choice_res, "probabilities", {"none": 1.0})
        p = probs.get(pick, 0.0)
    else:
        pick = "none"
        probs = {"none": 1.0}
        p = 1.0

    decision = JevDecision(
        name="resolve",
        choice=pick,
        p=p,
        probs=probs,
        model_version=getattr(jev, "_model", "jev-1.13"),
        latency_ms=ms,
    )

    # 5. Evaluate gate
    outcome = gate("resolve", pick, p, taus)
    if outcome == "escalate" or pick == "none":
        winning_cand = next((c for c in candidates if c.cid == pick), None)
        return ResolveResult(
            candidate=winning_cand or candidates[0],
            decision=decision,
            escalate=True,
            candidates=candidates,
        )

    winning_cand = next((c for c in candidates if c.cid == pick), None)
    return ResolveResult(
        candidate=winning_cand,
        decision=decision,
        escalate=False,
        candidates=candidates,
    )
