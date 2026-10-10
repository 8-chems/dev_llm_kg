from src.app.clients.llm import LLMClient


async def answer(question: str, llm_client: LLMClient) -> str:
    """Legacy Text2Cypher baseline answer generation."""
    return await llm_client.text2cypher_fallback(question)
