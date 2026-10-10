from src.app.clients.graph import GraphClient
from src.app.ingest.extract import Triple


MERGE_TRIPLE_CYPHER = """
MERGE (s:Entity {name: $sub})
ON CREATE SET s.id = $sub_id, s.labels = ['Entity', $sub_label], s.degree = 1
MERGE (o:Entity {name: $obj})
ON CREATE SET o.id = $obj_id, o.labels = ['Entity', $obj_label], o.degree = 1

WITH s, o
MERGE (s)-[r:RELATION {type: $rel}]->(o)
ON CREATE SET r.source_doc = $source_doc, r.confidence = $confidence, r.inferred = false
"""


async def merge_triple(
    graph: GraphClient, triple: Triple, source_doc: str
) -> None:
    """Merge grounded triple into Neo4j graph using MERGE on node entity IDs."""
    if not graph._driver or graph._is_mock:
        # Update in-memory mock store
        sub_id = f"ent_{triple.subject.lower().replace(' ', '_')}"
        obj_id = f"ent_{triple.object.lower().replace(' ', '_')}"
        graph._mock_nodes.append(
            {
                "node_id": sub_id,
                "name": triple.subject,
                "labels": ["Entity", triple.subject_label],
                "summary": "",
                "degree": 1,
            }
        )
        graph._mock_nodes.append(
            {
                "node_id": obj_id,
                "name": triple.object,
                "labels": ["Entity", triple.object_label],
                "summary": "",
                "degree": 1,
            }
        )
        graph._mock_edges.append(
            {
                "from_id": sub_id,
                "to_id": obj_id,
                "rel": triple.relation,
                "target_name": triple.object,
                "target_labels": ["Entity", triple.object_label],
                "confidence": triple.confidence,
                "degree": 1,
            }
        )
        return

    sub_id = f"ent_{triple.subject.lower().replace(' ', '_')}"
    obj_id = f"ent_{triple.object.lower().replace(' ', '_')}"

    async with graph._driver.session(
        database=graph._settings.neo4j_database
    ) as session:
        await session.run(
            MERGE_TRIPLE_CYPHER,
            sub=triple.subject,
            sub_id=sub_id,
            sub_label=triple.subject_label,
            obj=triple.object,
            obj_id=obj_id,
            obj_label=triple.object_label,
            rel=triple.relation,
            source_doc=source_doc,
            confidence=triple.confidence,
        )
