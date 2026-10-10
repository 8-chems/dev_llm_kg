import uuid
import asyncio
from typing import Any
from src.app.config import Settings
from src.app.models.ask import AskRequest, AskResponse
from src.app.models.trace import Trace
from src.app.models.decisions import Candidate
from src.app.clients.jev import JevClient, JevUnavailable
from src.app.clients.graph import GraphClient
from src.app.clients.llm import LLMClient
from src.app.flags.store import FlagStore
from src.app.review.queue import ReviewQueue
from src.app.obs.decision_log import DecisionLogger
from src.app.pipeline import parse as parse_module
from src.app.pipeline import resolve as resolve_module
from src.app.pipeline import navigate as navigate_module
from src.app.pipeline import escalate as escalate_module
from src.app.pipeline import narrate as narrate_module
from src.app.pipeline import legacy as legacy_module


class Orchestrator:

    def __init__(
        self,
        settings: Settings,
        jev: JevClient,
        graph: GraphClient,
        llm: LLMClient,
        flags: FlagStore,
        review_queue: ReviewQueue,
        decision_logger: DecisionLogger,
    ):
        self.settings = settings
        self.jev = jev
        self.graph = graph
        self.llm = llm
        self.flags = flags
        self.review_queue = review_queue
        self.decision_logger = decision_logger

    async def ask(self, req: AskRequest) -> AskResponse:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        mode = self.settings.pipeline_mode
        taus = self.flags.get_taus()

        # Check per-decision mode override
        resolve_flag = self.flags.get_flag("resolve")
        if resolve_flag.mode == "off" or mode == "off":
            legacy_ans = await legacy_module.answer(req.question, self.llm)
            empty_trace = Trace(
                request_id=request_id,
                start=None,
                hops=[],
                escalated_to="none",
                outcome="fallback",
            )
            return AskResponse(
                request_id=request_id,
                answer=legacy_ans,
                trace=empty_trace,
                mode="off",
                pending_review=False,
            )

        # Legacy task running concurrently for shadow / fallback
        legacy_task = (
            asyncio.create_task(legacy_module.answer(req.question, self.llm))
            if mode != "live"
            else None
        )

        trace = Trace(request_id=request_id)
        pending_review = False
        outcome = "accepted"
        final_answer = None

        try:
            # 1. Parse question
            parsed = await parse_module.parse(req.question, self.llm)
            lang = req.lang or parsed.lang

            # 2. Resolve entity
            res_out = await resolve_module.resolve(
                mention=parsed.entity,
                question=req.question,
                graph=self.graph,
                jev=self.jev,
                taus=taus,
                cap=self.settings.max_candidates,
            )

            self.decision_logger.log_decision(
                request_id=request_id,
                decision=res_out.decision,
                mode=mode,
                tau=taus.get("resolve", 0.85),
                outcome="escalate" if res_out.escalate else "accept",
            )

            start_cand = res_out.candidate

            if res_out.escalate:
                # Escalate resolve
                opts = [
                    {
                        "cid": c.cid,
                        "name": c.name,
                        "labels": c.labels,
                        "summary": c.summary,
                    }
                    for c in res_out.candidates
                ]
                esc_res = await escalate_module.handle_escalation(
                    request_id=request_id,
                    stage="resolve",
                    question=req.question,
                    options=opts,
                    llm_client=self.llm,
                    review_queue=self.review_queue,
                )
                trace.escalated_to = esc_res.escalated_to
                if esc_res.pending_review:
                    pending_review = True
                    outcome = "escalated"
                    trace.outcome = outcome
                    legacy_ans = (
                        await legacy_task
                        if legacy_task
                        else await legacy_module.answer(req.question, self.llm)
                    )
                    return AskResponse(
                        request_id=request_id,
                        answer=legacy_ans if mode == "shadow" else None,
                        trace=trace,
                        mode=mode,
                        pending_review=True,
                    )
                elif esc_res.choice_cid:
                    winning_c = next(
                        (
                            c
                            for c in res_out.candidates
                            if c.cid == esc_res.choice_cid
                        ),
                        start_cand,
                    )
                    start_cand = winning_c

            trace.start = start_cand

            # 3. Navigate graph
            if start_cand:
                nav_res = await navigate_module.navigate(
                    start=start_cand,
                    goal=parsed.goal,
                    question=req.question,
                    jev=self.jev,
                    graph=self.graph,
                    taus=taus,
                    max_hops=req.max_hops,
                    max_edges=self.settings.max_edges,
                )
                trace.hops = nav_res.path

                for hop in nav_res.path:
                    self.decision_logger.log_decision(
                        request_id=request_id,
                        decision=hop.decision,
                        mode=mode,
                        tau=taus.get("hop", 0.80),
                        outcome="accept",
                    )

                if nav_res.escalate:
                    esc_nav = await escalate_module.handle_escalation(
                        request_id=request_id,
                        stage="hop",
                        question=req.question,
                        options=nav_res.last_edges,
                        llm_client=self.llm,
                        review_queue=self.review_queue,
                    )
                    trace.escalated_to = esc_nav.escalated_to
                    if esc_nav.pending_review:
                        pending_review = True
                        outcome = "escalated"
                        trace.outcome = outcome
                        legacy_ans = (
                            await legacy_task
                            if legacy_task
                            else await legacy_module.answer(
                                req.question, self.llm
                            )
                        )
                        return AskResponse(
                            request_id=request_id,
                            answer=legacy_ans if mode == "shadow" else None,
                            trace=trace,
                            mode=mode,
                            pending_review=True,
                        )

            # Calculate min_p across trace decisions
            probs = [res_out.decision.p] + [h.decision.p for h in trace.hops]
            trace.min_p = min(probs) if probs else 1.0
            trace.outcome = "accepted"

            # 4. Narrate answer
            final_answer = await narrate_module.narrate(
                question=req.question,
                trace=trace,
                llm_client=self.llm,
                lang=lang,
            )

        except (JevUnavailable, TimeoutError, Exception) as e:
            outcome = "fallback"
            trace.outcome = "fallback"
            final_answer = (
                await legacy_task
                if legacy_task
                else await legacy_module.answer(req.question, self.llm)
            )

        if mode == "shadow":
            legacy_ans = (
                await legacy_task
                if legacy_task
                else await legacy_module.answer(req.question, self.llm)
            )
            return AskResponse(
                request_id=request_id,
                answer=legacy_ans,
                trace=trace,
                mode="shadow",
                pending_review=pending_review,
            )

        return AskResponse(
            request_id=request_id,
            answer=final_answer,
            trace=trace,
            mode=mode,
            pending_review=pending_review,
        )
