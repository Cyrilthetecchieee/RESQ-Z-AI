import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("RESQ_DB_PATH", "./resq.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
 id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL,
 latitude REAL NOT NULL, longitude REAL NOT NULL, severity INTEGER NOT NULL CHECK(severity BETWEEN 1 AND 5),
 status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL, risk_score REAL NOT NULL DEFAULT 0,
 risk_level TEXT NOT NULL DEFAULT 'low');
CREATE TABLE IF NOT EXISTS resources (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, kind TEXT NOT NULL,
 capabilities TEXT NOT NULL, latitude REAL NOT NULL, longitude REAL NOT NULL, available INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS allocations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER NOT NULL, resource_id INTEGER NOT NULL,
 start_at TEXT NOT NULL, end_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
 UNIQUE(resource_id, start_at, end_at), FOREIGN KEY(incident_id) REFERENCES incidents(id),
 FOREIGN KEY(resource_id) REFERENCES resources(id));
CREATE TABLE IF NOT EXISTS recommendations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, incident_id INTEGER NOT NULL, resource_id INTEGER NOT NULL,
 rationale TEXT NOT NULL, score REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 created_at TEXT NOT NULL, decided_at TEXT, FOREIGN KEY(incident_id) REFERENCES incidents(id),
 FOREIGN KEY(resource_id) REFERENCES resources(id));
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, entity_type TEXT NOT NULL,
 entity_id INTEGER, details TEXT NOT NULL, created_at TEXT NOT NULL);
"""

@contextmanager
def connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with connection() as conn:
        conn.executescript(SCHEMA)

def seed_db():
    if os.getenv("RESQ_SEED", "true").lower() != "true":
        return
    from .services import now
    with connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]:
            return
        incidents = [
            ("Flooded underpass", "Vehicles stranded after heavy rain", 40.7128, -74.0060, 4),
            ("Industrial fire", "Smoke reported at warehouse", 40.7200, -74.0100, 5),
            ("Medical assistance", "Multiple minor injuries at event", 40.7050, -74.0120, 3),
        ]
        conn.executemany("INSERT INTO incidents(title,description,latitude,longitude,severity,created_at) VALUES(?,?,?,?,?,?)",
                         [i + (now(),) for i in incidents])
        resources = [
            ("Rescue Unit 1", "vehicle", "water,rescue,medical", 40.7100, -74.0050),
            ("Fire Crew A", "team", "fire,medical", 40.7300, -74.0200),
            ("Medical Team 1", "team", "medical,first-aid", 40.7000, -74.0000),
            ("Drone 7", "drone", "survey,thermal", 40.7150, -74.0080),
        ]
        conn.executemany("INSERT INTO resources(name,kind,capabilities,latitude,longitude,available) VALUES(?,?,?,?,?,?)",
                         [r + (1,) for r in resources])
