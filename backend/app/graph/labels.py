"""String constants for all Neo4j labels and relationship types.

Source: memory-architecture-quack.md §2.1–2.3.
Cypher strings must be built from these constants, not literals — see
20-B1.md §2.2.
"""

from __future__ import annotations

# --- Node labels: canonical layer (§2.1) ---

EXAM = "Exam"
AREA = "Area"
SKILL = "Skill"
MISCONCEPTION = "Misconception"
TASK_TEMPLATE = "TaskTemplate"

# --- Node labels: personal layer (§2.2) ---

STUDENT = "Student"
KNOWLEDGE_STATE = "KnowledgeState"
EVIDENCE = "Evidence"
MISCONCEPTION_STATE = "MisconceptionState"

# --- Node labels: admission knowledge base (§2.3) ---

COUNTRY = "Country"
ADMISSION_ROUTE = "AdmissionRoute"
REQUIREMENT = "Requirement"
TEST_DATE = "TestDate"
SECTION = "Section"
SCALE_TABLE = "ScaleTable"
FACT = "Fact"

# --- Relationship types ---

HAS_AREA = "HAS_AREA"
HAS_SKILL = "HAS_SKILL"
REQUIRES = "REQUIRES"
ABOUT = "ABOUT"
TESTS = "TESTS"
TRAPS = "TRAPS"

HAS_STATE = "HAS_STATE"
FOR_SKILL = "FOR"
PREVIOUS = "PREVIOUS"
HAS_MISC_STATE = "HAS_MISC_STATE"
OF_MISCONCEPTION = "OF"
SUPPORTS = "SUPPORTS"
ROOT_CAUSE = "ROOT_CAUSE"
FROM_TEMPLATE = "FROM_TEMPLATE"
PART_OF = "PART_OF"
HAS_EVIDENCE = "HAS_EVIDENCE"

HAS_ROUTE = "HAS_ROUTE"
HAS_DATE = "HAS_DATE"
HAS_SECTION = "HAS_SECTION"
HAS_SCALE = "HAS_SCALE"