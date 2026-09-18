# Sync log

[YYYY-MM-DD HH:MM] [кто -> кому] что нужно и зачем
[2026-09-18 03:00] [B1 -> B3] Нужны модели из contracts §6 в apps/api/app/schemas/knowledge.py: SkillRef, SkillWeight, Prerequisite, KnowledgeStateOut, EvidenceContext, EvidenceIn, MisconceptionRef, ExamFormat, TestDate. Пока объявляю временно в своих модулях, перенесу на синке.
[2026-09-18 04:00] [B1 -> B3] Прошу добавить в корневой .gitignore строки для Python: __pycache__/, *.pyc, .venv/, .pytest_cache/, .ruff_cache/. Я пока не трогаю чужой файл, но pycache уже появляется в staging.
[2026-09-18 04:30] [B1 -> B3] Положил ВРЕМЕННЫЙ apps/api/app/schemas/knowledge.py с моделями из contracts §6 (SkillRef, SkillWeight, AreaOut, Prerequisite, KnowledgeStateOut, EvidenceContext, EvidenceIn, MisconceptionRef, Section, ExamFormat, TestDate, AdmissionRouteOut, FactOut). Нарушает твою зону, но чистая логика (app/knowledge, app/tasks) не может импортировать из app/graph (contracts §4.4), а schemas/ был пустой. На синке — merge или замена твоей версией.
[2026-09-18 06:00] [B1 -> B3] Допишу в apps/api/... (уже backend/app/schemas/tasks.py) три модели: Grade, AnswerIn, AnswerResult — они нужны для app/tasks/answer.py и перечислены в 00-contracts §6. Если у тебя в планах они свои — скажи.
