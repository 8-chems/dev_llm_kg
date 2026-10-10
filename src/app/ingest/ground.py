from typing import Any
from src.app.ingest.extract import Triple
from src.app.clients.jev import JevClient
from src.app.safety.untrusted import untrusted, UNTRUSTED_HEADER_INSTRUCTION


class NoulQuestionMock:

    def __init__(self, instructions: str):
        self.instructions = instructions


def build_ground_question() -> Any:
    instructions = (
        f"{UNTRUSTED_HEADER_INSTRUCTION} "
        "Does the source chunk text explicitly state or support this relationship?"
    )

    try:
        from typesafe_sdk import Noul

        return Noul(instructions=instructions)
    except Exception:
        return NoulQuestionMock(instructions=instructions)


async def ground_triple(
    chunk_text: str,
    triple: Triple,
    jev: JevClient,
    tau_ground: float = 0.90,
) -> tuple[bool, float]:
    """Verify extracted triple against text via Jev Noul question."""
    state = {
        "chunk_text": untrusted(chunk_text),
        "triple": untrusted(triple.model_dump()),
    }

    r, _ = await jev.decide(state, {"ground": build_ground_question()})

    noul_res = r.nouls.get("ground") if hasattr(r, "nouls") else None
    ground_p = (
        getattr(noul_res, "noul", 0.0)
        if noul_res
        else getattr(noul_res, "probability", 0.0)
        if hasattr(noul_res, "probability")
        else 0.88
    )

    accepted = ground_p >= tau_ground
    return accepted, ground_p
