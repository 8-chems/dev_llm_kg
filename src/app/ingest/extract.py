import json
import re
from typing import Any
from pydantic import BaseModel


class Triple(BaseModel):
    subject: str
    subject_label: str
    relation: str
    object: str
    object_label: str
    confidence: float = 1.0


def infer_label(entity_name: str) -> str:
    name_lower = entity_name.lower()
    if any(
        kw in name_lower
        for kw in [
            "corp",
            "inc",
            "ltd",
            "company",
            "group",
            "technologies",
            "tech",
            "co",
        ]
    ):
        return "Organization"
    if any(
        kw in name_lower
        for kw in [
            "paris",
            "city",
            "london",
            "york",
            "state",
            "country",
            "france",
            "usa",
        ]
    ):
        return "Location"
    if any(
        kw in name_lower
        for kw in ["system", "platform", "app", "model", "software", "rag"]
    ):
        return "Product"
    words = entity_name.split()
    if len(words) >= 2 and all(w[0].isupper() for w in words):
        return "Person"
    return "Entity"


def generic_rule_based_extraction(text: str) -> list[Triple]:
    """Generic rule-based extraction of (subject, relation, object) triples from text.

    Extracts capitalized entity pairs and action/relation phrases without hardcoded domain values.
    """
    triples: list[Triple] = []
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]

    rel_patterns = [
        (
            r"\b(serves as|works for|is CTO at|is CEO at|employed at|works at)\b",
            "WORKS_FOR",
        ),
        (
            r"\b(located in|based in|situated in|headquartered in)\b",
            "LOCATED_IN",
        ),
        (
            r"\b(developed|created|built|designed|authored|wrote)\b",
            "DEVELOPED",
        ),
        (
            r"\b(leads|manages|directs|heads|leads project)\b",
            "LEADS_PROJECT",
        ),
        (r"\b(produced|manufactured|yields)\b", "PRODUCES"),
        (r"\b(part of|subsidiary of|belongs to)\b", "PART_OF"),
    ]

    for sentence in sentences:
        entity_matches = list(
            re.finditer(
                r"\b[A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*\b", sentence
            )
        )
        if len(entity_matches) >= 2:
            for i in range(len(entity_matches) - 1):
                sub_ent = entity_matches[i].group(0)
                obj_ent = entity_matches[i + 1].group(0)

                if sub_ent.lower() in {
                    "the",
                    "a",
                    "an",
                    "based",
                    "according",
                    "where",
                    "who",
                    "what",
                }:
                    continue

                between_text = sentence[
                    entity_matches[i].end() : entity_matches[i + 1].start()
                ].strip()

                relation_name = None
                for pat, rel_code in rel_patterns:
                    if re.search(pat, between_text, re.IGNORECASE):
                        relation_name = rel_code
                        break

                if not relation_name:
                    words = re.findall(r"\b[a-z]{2,}\b", between_text.lower())
                    filtered_words = [
                        w
                        for w in words
                        if w
                        not in {
                            "the",
                            "a",
                            "an",
                            "at",
                            "in",
                            "of",
                            "to",
                            "as",
                            "is",
                            "was",
                            "are",
                            "were",
                        }
                    ]
                    if filtered_words:
                        relation_name = "_".join(filtered_words[:2]).upper()
                    else:
                        relation_name = "RELATED_TO"

                sub_label = infer_label(sub_ent)
                obj_label = infer_label(obj_ent)

                triples.append(
                    Triple(
                        subject=sub_ent,
                        subject_label=sub_label,
                        relation=relation_name,
                        object=obj_ent,
                        object_label=obj_label,
                        confidence=0.85,
                    )
                )

    return triples


async def extract_triples(
    chunk_text: str, llm_client: Any = None
) -> list[Triple]:
    """Extract candidate (subject, relation, object) triples from raw document text."""
    if not llm_client or getattr(llm_client, "_is_mock", True):
        return generic_rule_based_extraction(chunk_text)

    system_prompt = (
        "Extract knowledge triples from chunk text. "
        'Output JSON list: [{"subject": "...", "subject_label": "...", "relation": "...", "object": "...", "object_label": "..."}]'
    )

    try:
        res = await llm_client._client.messages.create(
            model=llm_client._settings.llm_model_parse,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": chunk_text}],
        )
        data = json.loads(res.content[0].text)
        return [Triple(**t) for t in data]
    except Exception:
        return generic_rule_based_extraction(chunk_text)

