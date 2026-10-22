# LinuxONE deployment guide

This project uses Python and SQLite rather than architecture-specific binaries.
The dependency set is intentionally small, but this repository has **not** been
deployed or certified on IBM LinuxONE. Verify every package in the target
environment before a production-like demonstration. Event code is SSF2026 .

## Prepare the host

```bash
uname -m
python3 --version
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip
git clone <your-repository-url> resq-z-ai
cd resq-z-ai
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`uname -m` should report the architecture supplied by the LinuxONE instance
(commonly `s390x`). If a wheel is unavailable, use a compatible source build
or omit the optional scikit-learn training dependency and use the documented
deterministic runtime fallback.

## Dependency and frontend readiness

The backend runtime is architecture-neutral Python/SQLite, but the pinned
dependency ranges are not a LinuxONE certification: `scikit-learn` (and its
NumPy/SciPy stack) may require an s390x source build or may be omitted outside
model training. Run `pip install -r requirements.txt` on the target s390x host
and retain the deterministic risk-scoring fallback if that optional stack is
unavailable. The React/Vite frontend is built separately with Node.js:

```bash
npm ci
npm run build
```

Serve `dist/` behind the same reverse proxy as the API, or set
`VITE_API_BASE_URL` and `VITE_WS_URL` at build time to the externally reachable
REST and WebSocket endpoints. The development Vite proxy is not used by a
production build. Verify `/health`, `/api/incidents`, and `/ws/events` through
that proxy before a demonstration.

## Configure and run

```bash
export RESQ_DB_PATH=/var/lib/resq-z-ai/resq.db
export RESQ_SEED=true
mkdir -p "$(dirname "$RESQ_DB_PATH")"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

Put the service behind authentication, TLS, and network controls before
exposing it. Do not expose development reload mode publicly.

## systemd example

Create `/etc/systemd/system/resq-z-ai.service` and replace the paths/user:

```ini
[Unit]
Description=RESQ-Z AI emergency decision support
After=network-online.target

[Service]
User=resq
WorkingDirectory=/opt/resq-z-ai
Environment=RESQ_DB_PATH=/var/lib/resq-z-ai/resq.db
Environment=RESQ_SEED=true
ExecStart=/opt/resq-z-ai/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now resq-z-ai
curl http://127.0.0.1:8000/health
journalctl -u resq-z-ai -f
```
