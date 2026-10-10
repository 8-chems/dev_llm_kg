import re
from src.app.models.trace import Trace
from src.app.clients.llm import LLMClient


def extract_proper_nouns(text: str) -> set[str]:
    """Basic extraction of capitalised proper noun phrases from generated text."""
    words = re.findall(r"\b[A-Z][a-z0-9_]+\b", text)
    return set(words)


def verify_narrated_entities(
    answer: str, trace: Trace, question: str
) -> bool:
    """Verify that all proper noun entities in the answer exist in the graph trace or question."""
    valid_names: set[str] = set()

    if trace.start:
        valid_names.add(trace.start.name.lower())
        for label in trace.start.labels:
            valid_names.add(label.lower())

    for hop in trace.hops:
        valid_names.add(hop.from_node.lower())
        valid_names.add(hop.to_node.lower())

    # Add question words to allowed set
    for q_word in question.lower().split():
        valid_names.add(q_word)

    # Standard stop words and connectives allowed
    allowed_words = {
        "the",
        "based",
        "on",
        "knowledge",
        "graph",
        "is",
        "are",
        "was",
        "were",
        "connected",
        "to",
        "from",
        "via",
        "in",
        "of",
        "and",
        "for",
        "with",
    }

    nouns = extract_proper_nouns(answer)
    for n in nouns:
        n_lower = n.lower()
        if n_lower in allowed_words:
            continue
        # Check if noun appears as substring in any valid name
        if not any(n_lower in v for v in valid_names):
            return False

    return True


async def narrate(
    question: str,
    trace: Trace,
    llm_client: LLMClient,
    lang: str = "en",
) -> str:
    """Narrate final answer with entity verification guard."""
    trace_data = trace.model_dump()
    raw_answer = await llm_client.narrate_answer(question, trace_data, lang=lang)

    # Code entity verification guard
    if verify_narrated_entities(raw_answer, trace, question):
        return raw_answer

    # Retry once with stricter prompt or fallback template
    stricter_answer = await llm_client.narrate_answer(
        f"STRICT MODE - DO NOT HALLUCINATE: {question}", trace_data, lang=lang
    )

    if verify_narrated_entities(stricter_answer, trace, question):
        return stricter_answer

    # Deterministic safe template fallback
    if trace.start and trace.hops:
        last = trace.hops[-1]
        return f"According to the graph, {trace.start.name} is connected to {last.to_node} via {last.rel_type}."
    elif trace.start:
        return f"Found entity {trace.start.name} in graph."
    return "The requested information could not be verified in the knowledge graph."
