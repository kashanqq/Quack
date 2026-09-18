# Sync log

[YYYY-MM-DD HH:MM] [кто -> кому] что нужно и зачем

[2026-09-18 12:49] [B3 -> B1] Нужны согласованные app.graph.client (create_driver/close_driver) и app.graph.queries.personal.ensure_student: без них Neo4j health и создание узла студента при /auth/me нельзя проверить сквозным тестом.
[2026-09-18 12:49] [B3 -> B2] Нужны app.llm.client.LLMClient(settings, redis) и app.agents.router: без них selection chat через реальный агент и LLM health остаются недоступны; B3 API возвращает 503.
