from typing import Any
from pydantic import BaseModel
from src.app.models.decisions import Candidate, Hop, JevDecision
from src.app.models.graph import EdgeRecord
from src.app.clients.graph import GraphClient
from src.app.clients.jev import JevClient
from src.app.pipeline.gate import gate
from src.app.safety.untrusted import untrusted, UNTRUSTED_HEADER_INSTRUCTION


class ChoiceQuestionMock:

    def __init__(self, instructions: str, criteria: dict[str, str]):
        self.instructions = instructions
        self.criteria = criteria


class NoulQuestionMock:

    def __init__(self, instructions: str):
        self.instructions = instructions


def build_hop_question(edges: list[EdgeRecord]) -> Any:
    criteria = {
        e.cid: f"{e.rel} -> {e.target_name} ({', '.join(e.target_labels)})"
        for e in edges
    }
    criteria["none"] = "None of these relationships leads toward the goal"
    instructions = (
        f"{UNTRUSTED_HEADER_INSTRUCTION} "
        "Which relationship best leads toward answering the question? "
        "Answer none if no relationship is relevant."
    )

    try:
        from typesafe_sdk import Choice

        return Choice(instructions=instructions, criteria=criteria)
    except Exception:
        return ChoiceQuestionMock(instructions=instructions, criteria=criteria)


def build_goal_question() -> Any:
    instructions = (
        f"{UNTRUSTED_HEADER_INSTRUCTION} "
        "Is the goal already answered at the current node and path?"
    )

    try:
        from typesafe_sdk import Noul

        return Noul(instructions=instructions)
    except Exception:
        return NoulQuestionMock(instructions=instructions)


class NavResult(BaseModel):
    path: list[Hop] = []
    done: bool = False
    escalate: bool = False
    last_edges: list[dict[str, Any]] = []


async def navigate(
    start: Candidate,
    goal: str,
    question: str,
    jev: JevClient,
    graph: GraphClient,
    taus: dict[str, float],
    max_hops: int = 3,
    max_edges: int = 50,
) -> NavResult:
    path: list[Hop] = []
    visited: set[str] = {start.node_id}
    current_node = start

    for hop_num in range(max_hops):
        edges = await graph.outgoing(
            current_node.node_id, cap=max_edges, exclude=visited
        )
        if not edges:
            break

        state = {
            "question": untrusted(question),
            "goal": goal,
            "current": untrusted(current_node.name),
            "path_so_far": [h.rel_type for h in path],
            "edges": [
                untrusted(
                    {
                        "cid": e.cid,
                        "rel": e.rel,
                        "target_name": e.target_name,
                        "target_labels": e.target_labels,
                    }
                )
                for e in edges
            ],
        }

        r, ms = await jev.decide(
            state,
            {
                "hop": build_hop_question(edges),
                "goal": build_goal_question(),
            },
        )

        choice_res = r.choices.get("hop") if hasattr(r, "choices") else None
        noul_res = r.nouls.get("goal") if hasattr(r, "nouls") else None

        if choice_res:
            pick = getattr(choice_res, "choice", "none")
            probs = getattr(choice_res, "probabilities", {"none": 1.0})
            p = probs.get(pick, 0.0)
        else:
            pick = "none"
            probs = {"none": 1.0}
            p = 1.0

        goal_p = (
            getattr(noul_res, "noul", 0.0)
            if noul_res
            else getattr(noul_res, "probability", 0.0)
            if hasattr(noul_res, "probability")
            else 0.0
        )

        hop_decision = JevDecision(
            name="hop",
            choice=pick,
            p=p,
            probs=probs,
            model_version=getattr(jev, "_model", "jev-1.13"),
            latency_ms=ms,
        )

        # Evaluate gate for hop choice
        if gate("hop", pick, p, taus) == "escalate":
            return NavResult(
                path=path,
                done=False,
                escalate=True,
                last_edges=[e.model_dump() for e in edges],
            )

        chosen_edge = next((e for e in edges if e.cid == pick), None)
        if not chosen_edge:
            return NavResult(
                path=path,
                done=False,
                escalate=True,
                last_edges=[e.model_dump() for e in edges],
            )

        visited.add(chosen_edge.to_id)
        hop_obj = Hop(
            from_node=current_node.name,
            rel_type=chosen_edge.rel,
            to_node=chosen_edge.target_name,
            decision=hop_decision,
            goal_p=goal_p,
        )
        path.append(hop_obj)

        current_node = Candidate(
            cid="current",
            node_id=chosen_edge.to_id,
            name=chosen_edge.target_name,
            labels=chosen_edge.target_labels,
        )

        tau_goal = taus.get("goal", 0.80)
        if goal_p >= tau_goal:
            return NavResult(path=path, done=True, escalate=False)

    return NavResult(path=path, done=False, escalate=True)
