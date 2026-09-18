# 1. Поднять БД и API
make up
make api  # в другом окне

# 2. Логин
curl -c cookies.txt -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@quack.kz","password":"quack-demo"}'

# 3. Шаг 4 — правка профиля
curl -b cookies.txt -X PATCH http://localhost:8000/profile \
  -H "Content-Type: application/json" \
  -d '{"path":"preferences.budget_per_year","value":50000,"by":"user"}'

# 4. Шаг 5 — сохранить программу и проверить overview
curl -b cookies.txt -X POST http://localhost:8000/saved/<program_id>
curl -b cookies.txt http://localhost:8000/overview | jq

# 5. Шаг 6 — старт замера
curl -b cookies.txt -X POST http://localhost:8000/diagnostic \
  -H "Content-Type: application/json" \
  -d '{"exam_id":"SAT_MATH","n_tasks":6}' | jq

# 6. Шаг 7 — выдать задачу и ответить
curl -b cookies.txt -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"skill_id":"sat.alg.slope_lines","set_id":null,"mode":"topic","with_trap":null,"exclude_seen":true}' | jq
curl -b cookies.txt -X POST http://localhost:8000/tasks/<instance_id>/answer \
  -H "Content-Type: application/json" \
  -d '{"instance_id":"<id>","answer":"A","time_spent_sec":20,"mode":"topic","after_guideline":false,"hint_level_before":0}' | jq

# 7. Шаг 8 — сет и прогноз
curl -b cookies.txt "http://localhost:8000/sets?exam_id=SAT_MATH" | jq