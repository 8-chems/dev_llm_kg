from src.app.clients.llm import LLMClient, ParsedQuestion


async def parse(question: str, llm_client: LLMClient) -> ParsedQuestion:
    """Parse user question into entity mention and goal using LLM."""
    return await llm_client.parse_question(question)
