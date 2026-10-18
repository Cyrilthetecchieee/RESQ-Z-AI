import asyncio
import random
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from .db import connection, init_db, seed_db
from .schemas import IncidentCreate, ResourceCreate, AllocationCreate, RecommendationDecision, WhatIf, SimulationControl
from .services import audit, distance, now, risk_assessment

class EventHub:
    def __init__(self): self.clients = set()
    async def publish(self, event):
        dead = set()
        for ws in self.clients:
            try: await ws.send_json(event)
            except Exception: dead.add(ws)
        self.clients -= dead

hub = EventHub()
simulation_enabled = True
_sim_task: asyncio.Task | None = None

_SYNTHETIC_INCIDENTS = [
    ("Road traffic collision",   "Multiple vehicles involved, possible trapped persons", 5),
    ("Structure fire",           "Smoke and flames at residential building, fire spreading", 5),
    ("Medical emergency",        "Cardiac arrest reported, bystander CPR in progress", 4),
    ("Flooding",                 "Low-lying area flooding after heavy rain, vehicles stranded", 4),
    ("Gas leak",                 "Strong gas odour near commercial district, evacuation advised", 3),
    ("Power line down",          "Downed live cable blocking road after storm damage", 3),
    ("Missing person",           "Vulnerable adult reported missing, last seen near riverbank", 2),
    ("Minor collision",          "Fender bender with minor injuries, road partially blocked", 2),
]

async def incident_generator():
    """Generate a synthetic incident every 15 s when simulation_enabled is True."""
    lat_base, lon_base = 40.72, -74.00
    while True:
        await asyncio.sleep(15)
        if not simulation_enabled:
            continue
        title, description, severity = random.choice(_SYNTHETIC_INCIDENTS)
        lat = round(lat_base + random.uniform(-0.05, 0.05), 4)
        lon = round(lon_base + random.uniform(-0.05, 0.05), 4)
        score, level = risk_assessment(severity, description)
        with connection() as c:
            cur = c.execute(
                """INSERT INTO incidents(title,description,latitude,longitude,severity,created_at,risk_score,risk_level)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (title, description, lat, lon, severity, now(), score, level),
            )
            audit(c, "simulate", "incident", cur.lastrowid, {"auto": True})
            result = row_dict(c.execute("SELECT * FROM incidents WHERE id=?", (cur.lastrowid,)).fetchone())
        await hub.publish({"type": "incident.created", "incident": result})

@asynccontextmanager
async def lifespan(app):
    global _sim_task
    init_db(); seed_db()
    _sim_task = asyncio.create_task(incident_generator())
    yield
    _sim_task.cancel()
    try:
        await _sim_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="RESQ-Z AI", version="0.1.0", lifespan=lifespan)

def row_dict(row): return dict(row) if row else None

@app.middleware("http")
async def api_compatibility_prefix(request: Request, call_next):
    if request.scope["path"].startswith("/api/"):
        request.scope["path"] = request.scope["path"][4:]
    return await call_next(request)

@app.get("/health")
def health(): return {"status": "ok"}

@app.post("/incidents", status_code=201)
async def create_incident(data: IncidentCreate):
    score, level = risk_assessment(data.severity, data.description)
    with connection() as c:
        cur = c.execute("""INSERT INTO incidents(title,description,latitude,longitude,severity,created_at,risk_score,risk_level)
                           VALUES(?,?,?,?,?,?,?,?)""", (*data.model_dump().values(), now(), score, level))
        audit(c, "create", "incident", cur.lastrowid, data.model_dump())
        result = row_dict(c.execute("SELECT * FROM incidents WHERE id=?", (cur.lastrowid,)).fetchone())
    await hub.publish({"type": "incident.created", "incident": result})
    return result

@app.get("/incidents")
def list_incidents(status: str | None = None):
    with connection() as c:
        q, args = "SELECT * FROM incidents", ()
        if status: q += " WHERE status=?"; args = (status,)
        return [row_dict(r) for r in c.execute(q + " ORDER BY id DESC", args)]

@app.get("/incidents/{incident_id}")
def get_incident(incident_id: int):
    with connection() as c: result = row_dict(c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone())
    if not result: raise HTTPException(404, "Incident not found")
    return result

@app.post("/incidents/{incident_id}/risk")
def assess_risk(incident_id: int):
    with connection() as c:
        r = c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not r: raise HTTPException(404, "Incident not found")
        score, level = risk_assessment(r["severity"], r["description"])
        c.execute("UPDATE incidents SET risk_score=?,risk_level=? WHERE id=?", (score, level, incident_id))
        audit(c, "assess", "incident", incident_id, {"score": score, "level": level})
        return {"incident_id": incident_id, "risk_score": score, "risk_level": level}

@app.post("/resources", status_code=201)
def create_resource(data: ResourceCreate):
    with connection() as c:
        cur = c.execute("INSERT INTO resources(name,kind,capabilities,latitude,longitude,available) VALUES(?,?,?,?,?,?)",
                        (data.name, data.kind, data.capabilities, data.latitude, data.longitude, int(data.available)))
        audit(c, "create", "resource", cur.lastrowid, data.model_dump())
        return row_dict(c.execute("SELECT * FROM resources WHERE id=?", (cur.lastrowid,)).fetchone())

@app.get("/resources")
def list_resources(available: bool | None = None):
    with connection() as c:
        q, args = "SELECT * FROM resources", ()
        if available is not None: q += " WHERE available=?"; args = (int(available),)
        return [row_dict(r) for r in c.execute(q, args)]

def _incident_resource(c, iid, rid):
    i = c.execute("SELECT * FROM incidents WHERE id=?", (iid,)).fetchone()
    r = c.execute("SELECT * FROM resources WHERE id=?", (rid,)).fetchone()
    if not i or not r: raise HTTPException(404, "Incident or resource not found")
    caps = {x.strip().lower() for x in r["capabilities"].split(",")}
    needed = "fire" if "fire" in i["description"].lower() else "medical" if "medical" in i["description"].lower() or i["severity"] <= 3 else "rescue"
    if needed not in caps and "survey" not in caps: raise HTTPException(409, f"Resource incompatible; requires {needed}")
    return i, r

@app.get("/incidents/{incident_id}/recommendations")
def recommendations(incident_id: int):
    with connection() as c:
        i = c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not i: raise HTTPException(404, "Incident not found")
        resources = c.execute("SELECT * FROM resources WHERE available=1").fetchall()
        needed = "fire" if "fire" in i["description"].lower() else "medical" if "medical" in i["description"].lower() or i["severity"] <= 3 else "rescue"
        out = []
        for r in resources:
            caps = {x.strip().lower() for x in r["capabilities"].split(",")}
            if needed in caps or "survey" in caps:
                score = round((100-distance(i["latitude"],i["longitude"],r["latitude"],r["longitude"])*3) + (10 if needed in caps else 0), 2)
                out.append({"resource_id": r["id"], "resource_name": r["name"], "score": score, "rationale": f"capability={needed}; proximity considered"})
                c.execute("""INSERT INTO recommendations(incident_id,resource_id,rationale,score,created_at)
                             VALUES(?,?,?,?,?)""",
                          (incident_id, r["id"], out[-1]["rationale"], score, now()))
        return sorted(out, key=lambda x: x["score"], reverse=True)

@app.post("/allocations", status_code=201)
async def allocate(data: AllocationCreate):
    if data.end_at <= data.start_at: raise HTTPException(422, "end_at must be after start_at")
    with connection() as c:
        c.execute("BEGIN IMMEDIATE")
        _incident_resource(c, data.incident_id, data.resource_id)
        overlap = c.execute("""SELECT id FROM allocations WHERE resource_id=? AND status='active'
          AND start_at < ? AND end_at > ?""", (data.resource_id, data.end_at.isoformat(), data.start_at.isoformat())).fetchone()
        if overlap: raise HTTPException(409, "Resource is already booked for this interval")
        cur = c.execute("INSERT INTO allocations(incident_id,resource_id,start_at,end_at) VALUES(?,?,?,?)",
                        (data.incident_id, data.resource_id, data.start_at.isoformat(), data.end_at.isoformat()))
        c.execute("UPDATE resources SET available=0 WHERE id=?", (data.resource_id,))
        audit(c, "allocate", "allocation", cur.lastrowid, data.model_dump(mode="json"))
        result = row_dict(c.execute("SELECT * FROM allocations WHERE id=?", (cur.lastrowid,)).fetchone())
    await hub.publish({"type": "allocation.created", "allocation": result})
    return result

@app.post("/recommendations/{incident_id}/decision")
async def recommendation_decision(incident_id: int, data: RecommendationDecision):
    if data.decision == "override" and data.resource_id is None: raise HTTPException(422, "resource_id required for override")
    with connection() as c:
        c.execute("BEGIN IMMEDIATE")
        i = c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not i: raise HTTPException(404, "Incident not found")
        resource_id = data.resource_id
        if data.decision == "approve":
            rec = c.execute("SELECT * FROM recommendations WHERE incident_id=? AND status='pending' ORDER BY score DESC LIMIT 1", (incident_id,)).fetchone()
            if not rec: raise HTTPException(404, "No pending recommendation")
            resource_id = rec["resource_id"]
        if data.decision in ("approve", "override"):
            # Use a one-hour allocation and preserve all overlap checks.
            from datetime import timedelta
            start = datetime_from(i["created_at"]); end = start + timedelta(hours=1)
            _incident_resource(c, incident_id, resource_id)
            overlap = c.execute("SELECT id FROM allocations WHERE resource_id=? AND status='active' AND start_at<? AND end_at>?",
                                (resource_id, end.isoformat(), start.isoformat())).fetchone()
            if overlap: raise HTTPException(409, "Resource is already booked")
            c.execute("INSERT INTO allocations(incident_id,resource_id,start_at,end_at) VALUES(?,?,?,?)",
                      (incident_id, resource_id, start.isoformat(), end.isoformat()))
            c.execute("UPDATE resources SET available=0 WHERE id=?", (resource_id,))
        c.execute("UPDATE recommendations SET status=?, decided_at=? WHERE incident_id=? AND status='pending'",
                  ("approved" if data.decision == "approve" else "overridden" if data.decision == "override" else "rejected",
                   now(), incident_id))
        audit(c, data.decision, "incident", incident_id, {"resource_id": resource_id, "reason": data.reason})
        return {"incident_id": incident_id, "decision": data.decision, "resource_id": resource_id}

def datetime_from(value):
    from datetime import datetime
    return datetime.fromisoformat(value)

@app.post("/incidents/{incident_id}/what-if")
def what_if(incident_id: int, data: WhatIf):
    with connection() as c:
        i = c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not i: raise HTTPException(404, "Incident not found")
        score, level = risk_assessment(data.severity if data.severity is not None else i["severity"], data.description or i["description"])
        return {"incident_id": incident_id, "risk_score": score, "risk_level": level, "baseline_score": i["risk_score"]}

@app.get("/audit")
def audit_events(limit: int = 100):
    if limit < 1 or limit > 1000: raise HTTPException(422, "limit must be 1..1000")
    with connection() as c: return [row_dict(r) for r in c.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]

@app.get("/metrics")
def metrics():
    with connection() as c:
        return {"incidents": c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0],
                "open_incidents": c.execute("SELECT COUNT(*) FROM incidents WHERE status='open'").fetchone()[0],
                "resources": c.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
                "active_allocations": c.execute("SELECT COUNT(*) FROM allocations WHERE status='active'").fetchone()[0]}

@app.post("/simulation")
def simulation(data: SimulationControl):
    global simulation_enabled
    simulation_enabled = data.enabled
    return {"enabled": simulation_enabled}

@app.post("/simulation/start")
def simulation_start():
    global simulation_enabled
    simulation_enabled = True
    return {"enabled": simulation_enabled}

@app.post("/simulation/pause")
def simulation_pause():
    global simulation_enabled
    simulation_enabled = False
    return {"enabled": simulation_enabled}

@app.post("/simulation/reset")
async def simulation_reset():
    global simulation_enabled
    simulation_enabled = False
    with connection() as c:
        # Delete in FK-safe order
        c.execute("DELETE FROM recommendations")
        c.execute("DELETE FROM allocations")
        c.execute("DELETE FROM audit_log")
        c.execute("DELETE FROM incidents")
        c.execute("DELETE FROM resources")
        # Reset auto-increment counters so IDs restart from 1
        c.execute("DELETE FROM sqlite_sequence WHERE name IN ('incidents','resources','allocations','recommendations','audit_log')")
    seed_db()
    with connection() as c:
        incidents = [row_dict(r) for r in c.execute("SELECT * FROM incidents ORDER BY id ASC")]
    await hub.publish({"type": "simulation.reset", "incidents": incidents})
    return {"enabled": False, "message": "Simulation reset; seed data restored."}

@app.websocket("/ws/events")
async def events(websocket: WebSocket):
    await websocket.accept(); hub.clients.add(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True: await websocket.receive_text()
    except WebSocketDisconnect: hub.clients.discard(websocket)
