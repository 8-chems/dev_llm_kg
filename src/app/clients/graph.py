from typing import Any
from neo4j import AsyncGraphDatabase
from src.app.config import Settings
from src.app.models.graph import NodeRecord, EdgeRecord


START_FULLTEXT = """
CALL db.index.fulltext.queryNodes('entity_names', $q) YIELD node, score
RETURN elementId(node) AS node_id, node.id AS entity_id, node.name AS name, labels(node) AS labels,
       coalesce(node.summary,'') AS summary, score
ORDER BY score DESC LIMIT $cap
"""

START_MATCH_FALLBACK = """
MATCH (n:Entity)
WHERE toLower(n.name) CONTAINS toLower($q_text)
   OR any(alias IN coalesce(n.aliases, []) WHERE toLower(alias) CONTAINS toLower($q_text))
RETURN elementId(n) AS node_id, n.id AS entity_id, n.name AS name, labels(n) AS labels,
       coalesce(n.summary,'') AS summary, 1.0 AS score
ORDER BY coalesce(n.degree, 0) DESC LIMIT $cap
"""

OUTGOING_CAPPED = """
MATCH (n) WHERE elementId(n) = $node_id OR n.id = $node_id
MATCH (n)-[r]->(m)
WHERE size($allowed_rels) = 0 OR type(r) IN $allowed_rels
RETURN elementId(m) AS to_id, m.id AS target_entity_id, type(r) AS rel, m.name AS target_name,
       labels(m) AS target_labels, coalesce(m.degree,0) AS degree, coalesce(r.confidence,1.0) AS confidence
ORDER BY coalesce(r.confidence,1.0) DESC, degree DESC
LIMIT $cap
"""


class GraphClient:

    def __init__(self, settings: Settings):
        self._settings = settings
        self._driver = None
        self._is_mock = False

        if (
            "localhost" in settings.neo4j_uri
            or "bolt://" in settings.neo4j_uri
        ):
            try:
                self._driver = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(
                        settings.neo4j_username,
                        settings.neo4j_password.get_secret_value(),
                    ),
                )
            except Exception as e:
                self._is_mock = True
    async def _search_candidates(
        self, mention: str, cap: int
    ) -> list[NodeRecord]:
        """Search for candidate nodes in the graph."""
        if self._is_mock:
            return self._search_mock_candidates(mention, cap)

        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                async with self._driver.session(
                    database=self._settings.neo4j_database
                ) as session:
                    res = await session.run(START_FULLTEXT, q=mention, cap=cap)
                    records = await res.data()
                    return [NodeRecord(**r) for r in records]
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
                print(f"Failed to connect to Neo4j: {e}")
        else:
            self._is_mock = True

        # In-memory seed graph for fallback/mock testing
        self._mock_nodes: list[dict[str, Any]] = [
            {
                "node_id": "ent_acme",
                "name": "Acme Corp",
                "labels": ["Entity", "Organization"],
                "summary": "A global enterprise software company",
                "degree": 3,
            },
            {
                "node_id": "ent_paris",
                "name": "Paris",
                "labels": ["Entity", "Location"],
                "summary": "Capital city of France",
                "degree": 2,
            },
            {
                "node_id": "ent_alice",
                "name": "Alice Dupont",
                "labels": ["Entity", "Person"],
                "summary": "Chief Technology Officer at Acme Corp",
                "degree": 2,
            },
            {
                "node_id": "ent_bob",
                "name": "Bob Martin",
                "labels": ["Entity", "Person"],
                "summary": "Lead AI Architect at Acme Corp",
                "degree": 2,
            },
            {
                "node_id": "ent_graphrag",
                "name": "GraphRAG System",
                "labels": ["Entity", "Product"],
                "summary": "Next-gen graph-augmented search platform",
                "degree": 2,
            },
        ]

        self._mock_edges: list[dict[str, Any]] = [
            {
                "from_id": "ent_alice",
                "to_id": "ent_acme",
                "rel": "WORKS_FOR",
                "target_name": "Acme Corp",
                "target_labels": ["Entity", "Organization"],
                "confidence": 1.0,
                "degree": 3,
            },
            {
                "from_id": "ent_bob",
                "to_id": "ent_acme",
                "rel": "WORKS_FOR",
                "target_name": "Acme Corp",
                "target_labels": ["Entity", "Organization"],
                "confidence": 1.0,
                "degree": 3,
            },
            {
                "from_id": "ent_acme",
                "to_id": "ent_paris",
                "rel": "LOCATED_IN",
                "target_name": "Paris",
                "target_labels": ["Entity", "Location"],
                "confidence": 0.95,
                "degree": 2,
            },
            {
                "from_id": "ent_alice",
                "to_id": "ent_graphrag",
                "rel": "LEADS_PROJECT",
                "target_name": "GraphRAG System",
                "target_labels": ["Entity", "Product"],
                "confidence": 0.99,
                "degree": 2,
            },
            {
                "from_id": "ent_bob",
                "to_id": "ent_graphrag",
                "rel": "DEVELOPED",
                "target_name": "GraphRAG System",
                "target_labels": ["Entity", "Product"],
                "confidence": 0.98,
                "degree": 2,
            },
        ]

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def search_candidates(
        self, mention: str, cap: int = 50
    ) -> list[NodeRecord]:
        """Search entity candidates by text mention via fulltext index or fallback."""
        if not self._driver or self._is_mock:
            return self._search_mock_candidates(mention, cap)

        try:
            async with self._driver.session(
                database=self._settings.neo4j_database
            ) as session:
                try:
                    res = await session.run(
                        START_FULLTEXT, q=f"{mention}~", cap=cap
                    )
                    records = await res.data()
                except Exception:
                    res = await session.run(
                        START_MATCH_FALLBACK, q_text=mention, cap=cap
                    )
                    records = await res.data()

                return [
                    NodeRecord(
                        node_id=str(r.get("node_id") or r.get("entity_id")),
                        name=r["name"],
                        labels=list(r["labels"]),
                        summary=r.get("summary", ""),
                        degree=r.get("degree", 0),
                    )
                    for r in records
                ]
        except Exception:
            return self._search_mock_candidates(mention, cap)

    async def outgoing(
        self,
        node_id: str,
        cap: int = 50,
        exclude: set[str] | None = None,
        allowed_rels: list[str] | None = None,
    ) -> list[EdgeRecord]:
        """Fetch capped outgoing edges from a node, excluding visited target nodes."""
        exclude_set = exclude or set()
        allowed = (
            allowed_rels
            if allowed_rels is not None
            else self._settings.allowed_rels
        )

        if not self._driver or self._is_mock:
            return self._get_mock_outgoing(node_id, cap, exclude_set, allowed)

        try:
            async with self._driver.session(
                database=self._settings.neo4j_database
            ) as session:
                res = await session.run(
                    OUTGOING_CAPPED,
                    node_id=node_id,
                    cap=cap * 2,
                    allowed_rels=allowed,
                )
                records = await res.data()

                edges: list[EdgeRecord] = []
                idx = 0
                for r in records:
                    to_id = str(
                        r.get("to_id") or r.get("target_entity_id", "")
                    )
                    if to_id in exclude_set:
                        continue
                    cid = f"c{idx}"
                    edges.append(
                        EdgeRecord(
                            cid=cid,
                            from_id=node_id,
                            to_id=to_id,
                            rel=r["rel"],
                            target_name=r["target_name"],
                            target_labels=list(r["target_labels"]),
                            confidence=float(r.get("confidence", 1.0)),
                            degree=int(r.get("degree", 0)),
                        )
                    )
                    idx += 1
                    if len(edges) >= cap:
                        break
                return edges
        except Exception:
            return self._get_mock_outgoing(node_id, cap, exclude_set, allowed)

    def _search_mock_candidates(
        self, mention: str, cap: int
    ) -> list[NodeRecord]:
        mention_lower = mention.lower()
        matches = []
        for n in self._mock_nodes:
            if (
                mention_lower in n["name"].lower()
                or mention_lower in n["summary"].lower()
            ):
                matches.append(NodeRecord(**n))
        if not matches:
            matches = [NodeRecord(**n) for n in self._mock_nodes[:cap]]
        return matches[:cap]

    def _get_mock_outgoing(
        self,
        node_id: str,
        cap: int,
        exclude: set[str],
        allowed: list[str],
    ) -> list[EdgeRecord]:
        edges = []
        idx = 0
        for e in self._mock_edges:
            if e["from_id"] == node_id and e["to_id"] not in exclude:
                if allowed and e["rel"] not in allowed:
                    continue
                cid = f"c{idx}"
                edges.append(
                    EdgeRecord(
                        cid=cid,
                        from_id=node_id,
                        to_id=e["to_id"],
                        rel=e["rel"],
                        target_name=e["target_name"],
                        target_labels=e["target_labels"],
                        confidence=e["confidence"],
                        degree=e["degree"],
                    )
                )
                idx += 1
                if len(edges) >= cap:
                    break
        return edges
