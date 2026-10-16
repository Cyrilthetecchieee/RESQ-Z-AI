# RESQ-Z AI backend

Real-time emergency decision support for the **Real-Time AI for Critical Decisions**
hackathon theme. This is a simulated, human-in-the-loop prototype: it does not
ingest emergency calls, contain patient data, or provide medically validated advice.

## Run locally

### Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://127.0.0.1:8000`; both `/health` and `/api/health`
are supported. SQLite is created at `RESQ_DB_PATH` (default `./resq.db`).

### Frontend

```powershell
npm install
npm run dev
```

Open the Vite URL shown in the terminal. Its development proxy forwards `/api`
and `/ws` to the backend.

## Verification

```powershell
pytest
npm run build
python -m ml.train_risk_model
```

The scikit-learn model-training script uses deterministic synthetic data and
reports evaluation output. Runtime risk scoring has a deterministic fallback.

## Implemented surfaces

* FastAPI REST API, WebSocket event hub, SQLite seed data, audit log, metrics,
  recommendations, what-if scoring, approval/rejection/override, and
  overlap-protected allocations.
* React mission-control dashboard with six operational views, simulation
  controls, incident creation, charts, filters, and accessible map-style view.
* Synthetic risk-model training/evaluation and LinuxONE deployment guidance.

## QA status

The current local QA run reports 36 backend tests passing, a passing frontend
production build, and measured endpoint latency in
[docs/TESTING_REPORT.md](docs/TESTING_REPORT.md). The scikit-learn evaluation is
deliberately documented as rule-learning on synthetic labels. LinuxONE/s390x
installation and deployment remain unverified. The simulation controls are
state toggles rather than a background event scheduler, and the frontend
secondary pages are operational shells rather than fully populated workflows.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/API_REFERENCE.md](docs/API_REFERENCE.md),
and [docs/LINUXONE_DEPLOYMENT.md](docs/LINUXONE_DEPLOYMENT.md) for details. backend

FastAPI prototype with a local SQLite database. Run with:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API seeds deterministic incidents/resources on startup. Set `RESQ_DB_PATH`
and `RESQ_SEED=false` to customize persistence.
