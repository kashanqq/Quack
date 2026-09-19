// Quack! — Neo4j schema (indices and constraints).
// Source: 20-B1.md §2.2, 00-contracts-phase2.md §3.5, memory-architecture-quack.md §2.4.
// $dim is a placeholder — replaced at load time with settings.EMBEDDING_DIM
// by app/graph/schema.py::apply_schema.

// --- Vector index for Misconception embeddings (personal + library) ---

CREATE VECTOR INDEX misc_emb IF NOT EXISTS
FOR (m:Misconception) ON m.embedding
OPTIONS {
  indexConfig: {
    `vector.dimensions`: $dim,
    `vector.similarity_function`: 'cosine'
  }
};

// --- Uniqueness constraints ---

CREATE CONSTRAINT skill_id_unique IF NOT EXISTS
FOR (s:Skill) REQUIRE s.id IS UNIQUE;

CREATE CONSTRAINT template_id_unique IF NOT EXISTS
FOR (t:TaskTemplate) REQUIRE t.id IS UNIQUE;

CREATE CONSTRAINT misc_id_unique IF NOT EXISTS
FOR (m:Misconception) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT student_id_unique IF NOT EXISTS
FOR (s:Student) REQUIRE s.id IS UNIQUE;

// --- Secondary indices: phase 1 ---

CREATE INDEX evidence_key IF NOT EXISTS
FOR (e:Evidence) ON (e.event_id, e.skill_id, e.ordinal);

CREATE INDEX ks_student IF NOT EXISTS
FOR (k:KnowledgeState) ON (k.student_id, k.exam_id);

CREATE INDEX ms_status IF NOT EXISTS
FOR (m:MisconceptionState) ON (m.student_id, m.status);

// --- Secondary indices: phase 2 (00-contracts-phase2.md §3.5) ---

CREATE INDEX ms_lookup IF NOT EXISTS
FOR (m:MisconceptionState) ON (m.student_id, m.misconception_id);

CREATE INDEX evidence_recent IF NOT EXISTS
FOR (e:Evidence) ON (e.student_id, e.observed_at);

// Evidence context lookups: «какое сообщение / какой экземпляр задачи»
// (memory-architecture §10.5, explain_belief).

CREATE INDEX evidence_ctx_instance IF NOT EXISTS
FOR (e:Evidence) ON (e.ctx_instance_id);

CREATE INDEX evidence_ctx_message IF NOT EXISTS
FOR (e:Evidence) ON (e.ctx_message_id);