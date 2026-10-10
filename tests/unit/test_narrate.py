from src.app.models.trace import Trace
from src.app.models.decisions import Candidate, Hop, JevDecision
from src.app.pipeline.narrate import verify_narrated_entities


def test_verify_narrated_entities_valid():
    start = Candidate(cid="c0", node_id="ent_acme", name="Acme Corp", labels=["Organization"])
    decision = JevDecision(name="hop", choice="c0", p=0.9, model_version="1.0", latency_ms=10)
    hop = Hop(from_node="Acme Corp", rel_type="LOCATED_IN", to_node="Paris", decision=decision)
    trace = Trace(request_id="r1", start=start, hops=[hop])

    answer = "Based on the knowledge graph, Acme Corp is located in Paris."
    assert verify_narrated_entities(answer, trace, "Where is Acme Corp?")


def test_verify_narrated_entities_hallucinated():
    start = Candidate(cid="c0", node_id="ent_acme", name="Acme Corp", labels=["Organization"])
    trace = Trace(request_id="r1", start=start, hops=[])

    answer = "Based on the knowledge graph, Acme Corp was founded by Microsoft."
    assert not verify_narrated_entities(answer, trace, "Where is Acme Corp?")
