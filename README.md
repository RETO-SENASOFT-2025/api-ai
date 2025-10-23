python -m venv .venv
.venv\Scripts\Activate

<!-- Una vez -->

pip install --upgrade pip wheel setuptools cryptography
pip install -r requirements.txt --upgrade

<!-- Varias veces -->

python -m ruff check .
python -m ruff format .

# ETL del dataset
- Instala dependencias: `pip install -r requirements.txt`
- Ejecuta ETL: `python -m etl.main_etl`
- Base SQLite: `data/db/reports.sqlite`
- Tablas: `reports` (principal) y `report_search` (FTS)

# Docker (ETL en un solo comando)
- Ejecuta ETL: `docker compose run --rm etl`
- Dataset: `DATASET_PATH=/app/data/dataset/dataset.csv` (montado desde `./data/dataset/`), si no existe usa `./internal/assets/dataset.csv`.
- Salidas:
  - `data/db/reports.sqlite`
- FTS5: disponible en el contenedor; la tabla virtual `report_search` se crea si la librería SQLite soporta FTS5.

# API local (sin Docker)
- Instala dependencias mínimas: `pip install fastapi uvicorn httpx`
- Ajusta `DB_PATH` si deseas otro SQLite (por defecto `data/db/reports.sqlite`).
- Ajusta `LLM_URL` si tu servidor de LLM no está en `http://localhost:8081`.
- Arranca la API: `uvicorn app.main:app --host 0.0.0.0 --port 8011`
- Status: `curl http://localhost:8011/status`
- Consulta (devuelve solo la respuesta):
  - `curl -X POST http://localhost:8011/ask -H "Content-Type: application/json" -d '{"texto":"¿Cuáles son los principales problemas en Medellín?"}'`
- Comportamiento sin evidencia: si no hay contexto relevante, la API no invoca al LLM y devuelve: "No hay evidencia suficiente en la base de datos para responder esta consulta."

# API + LLM con Docker
- Descarga el modelo: `docker compose run --rm model-puller`
- Arranca los servicios: `docker compose up -d llm api`
- Ruta del modelo: `./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf`
- La API: `http://localhost:8011` y el LLM: `http://localhost:8081`
- Consulta (devuelve solo la respuesta):
  - `curl -X POST http://localhost:8011/ask -H "Content-Type: application/json" -d '{"texto":"¿Cuáles son los principales problemas en Medellín?"}'`
- Timeouts y rendimiento:
  - Ajusta `LLM_TIMEOUT_SECONDS` (por defecto `180`) y `N_PREDICT` (por defecto `80`) vía variables de entorno si lo necesitas.

-> deactivate