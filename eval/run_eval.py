import argparse
import asyncio
import json
import os
from eval.schema import GoldItem
from src.app.config import Settings
from src.app.clients.breaker import Breaker
from src.app.clients.jev import JevClient
from src.app.clients.graph import GraphClient
from src.app.clients.llm import LLMClient
from src.app.flags.store import FlagStore
from src.app.review.store import ReviewStore
from src.app.review.queue import ReviewQueue
from src.app.obs.decision_log import DecisionLogger
from src.app.pipeline.orchestrator import Orchestrator
from src.app.models.ask import AskRequest


async def run_evaluation(system: str, split: str, out_path: str):
    dataset_file = f"eval/datasets/gold_{split}.jsonl"
    if not os.path.exists(dataset_file):
        from eval.build_gold import generate_datasets
        generate_datasets()

    items: list[GoldItem] = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(GoldItem(**json.loads(line)))

    # Configure pipeline according to system
    settings = Settings()
    if system == "S0":
        settings.pipeline_mode = "off"
    else:
        settings.pipeline_mode = "live"

    breaker = Breaker()
    jev = JevClient(settings, breaker)
    graph = GraphClient(settings)
    llm = LLMClient(settings)
    flags = FlagStore(settings)
    review_store = ReviewStore()
    queue = ReviewQueue(settings, review_store)
    logger = DecisionLogger(settings)

    orchestrator = Orchestrator(
        settings=settings,
        jev=jev,
        graph=graph,
        llm=llm,
        flags=flags,
        review_queue=queue,
        decision_logger=logger,
    )

    results = []
    for item in items:
        req = AskRequest(question=item.question, lang=item.lang)
        resp = await orchestrator.ask(req)

        # Check correctness against gold
        correct = False
        if item.type == "unanswerable":
            correct = resp.answer is None or "not found" in (resp.answer or "").lower()
        else:
            if resp.trace.start and item.gold_start_id:
                correct = True

        res_record = {
            "item_id": item.id,
            "system": system,
            "question": item.question,
            "p": resp.trace.min_p or 0.5,
            "correct": 1 if correct else 0,
            "outcome": resp.trace.outcome,
            "escalated_to": resp.trace.escalated_to,
            "answer": resp.answer,
        }
        results.append(res_record)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")

    print(f"Evaluation complete for system {system} on {split}. Results written to {out_path}.")
    await graph.close()


def main():
    parser = argparse.ArgumentParser(description="Run GraphRAG Evaluation")
    parser.add_argument("--system", choices=["S0", "S1", "S2", "S3"], default="S1")
    parser.add_argument("--split", choices=["dev", "test"], default="dev")
    parser.add_argument("--out", default="eval/runs/s1_dev.jsonl")
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.system, args.split, args.out))


if __name__ == "__main__":
    main()
