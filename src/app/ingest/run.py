import asyncio
from src.app.config import Settings
from src.app.clients.breaker import Breaker
from src.app.clients.jev import JevClient
from src.app.clients.graph import GraphClient
from src.app.clients.llm import LLMClient
from src.app.ingest.extract import extract_triples
from src.app.ingest.ground import ground_triple
from src.app.ingest.merge import merge_triple


async def run_ingestion_pipeline(documents: list[dict[str, str]]) -> None:
    settings = Settings()
    breaker = Breaker()
    jev = JevClient(settings, breaker)
    graph = GraphClient(settings)
    llm = LLMClient(settings)

    print(f"Starting ingestion for {len(documents)} document chunks...")

    for doc in documents:
        doc_id = doc["id"]
        text = doc["text"]
        print(f"Extracting triples from document {doc_id}...")

        triples = await extract_triples(text, llm)
        print(f"Extracted {len(triples)} triples from {doc_id}.")

        for t in triples:
            accepted, p = await ground_triple(text, t, jev)
            if accepted:
                print(f"Triple accepted (p={p:.2f}): {t.subject} -[{t.relation}]-> {t.object}")
                await merge_triple(graph, t, doc_id)
            else:
                print(f"Triple flagged for review (p={p:.2f}): {t.subject} -[{t.relation}]-> {t.object}")

    await graph.close()
    print("Ingestion pipeline finished.")


if __name__ == "__main__":
    sample_docs = [
        {
            "id": "doc_001",
            "text": "Alice Dupont serves as Chief Technology Officer at Acme Corp in Paris.",
        },
        {
            "id": "doc_002",
            "text": "Bob Martin developed the GraphRAG System at Acme Corp.",
        },
    ]
    asyncio.run(run_ingestion_pipeline(sample_docs))
