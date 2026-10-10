from typing import Literal
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "dev"
    pipeline_mode: Literal["off", "shadow", "live"] = "shadow"

    # Jev settings
    typesafe_api_key: SecretStr = SecretStr("ts_test_key")
    jev_model: str = "jev-1.13"
    jev_timeout_s: float = 2.0
    jev_base_url: str | None = None  # set for OpenRouter etc.

    # Neo4j settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("password")
    neo4j_database: str = "neo4j"

    # LLM settings
    anthropic_api_key: SecretStr = SecretStr("sk-ant-test")
    llm_model_parse: str = "claude-haiku-4-5-20251001"
    llm_model_review: str = "claude-opus-5-5"
    llm_model_narrate: str = "claude-sonnet-5-5"

    # Pipeline settings
    max_candidates: int = 50
    max_edges: int = 50
    max_hops: int = 3
    thresholds_path: str = "eval/thresholds/thresholds.json"
    allowed_rels: list[str] = []  # empty = all allowed

    # GCP infra settings
    gcp_project: str = "dev-graphrag-gcp"
    pubsub_topic: str = "escalations"
    bq_dataset: str = "decisions"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )
