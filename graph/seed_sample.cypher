// Seed data for local testing and integration
MERGE (acme:Entity:Organization {id: "ent_acme", name: "Acme Corp", aliases: ["Acme", "Acme Inc"], summary: "A global enterprise software company", degree: 3})
MERGE (paris:Entity:Location {id: "ent_paris", name: "Paris", aliases: ["City of Light"], summary: "Capital city of France", degree: 2})
MERGE (alice:Entity:Person {id: "ent_alice", name: "Alice Dupont", aliases: ["Alice D."], summary: "Chief Technology Officer at Acme Corp", degree: 2})
MERGE (bob:Entity:Person {id: "ent_bob", name: "Bob Martin", aliases: ["Bob"], summary: "Lead AI Architect at Acme Corp", degree: 2})
MERGE (graphrag:Entity:Product {id: "ent_graphrag", name: "GraphRAG System", aliases: ["Jev GraphRAG"], summary: "Next-gen graph-augmented search platform", degree: 2})

MERGE (alice)-[r1:WORKS_FOR {confidence: 1.0, inferred: false, source_doc: "doc_01"}]->(acme)
MERGE (bob)-[r2:WORKS_FOR {confidence: 1.0, inferred: false, source_doc: "doc_01"}]->(acme)
MERGE (acme)-[r3:LOCATED_IN {confidence: 0.95, inferred: false, source_doc: "doc_02"}]->(paris)
MERGE (alice)-[r4:LEADS_PROJECT {confidence: 0.99, inferred: false, source_doc: "doc_03"}]->(graphrag)
MERGE (bob)-[r5:DEVELOPED {confidence: 0.98, inferred: false, source_doc: "doc_03"}]->(graphrag)
