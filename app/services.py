import json
import math
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()

def distance(a_lat, a_lon, b_lat, b_lon):
    return math.hypot((a_lat-b_lat) * 111, (a_lon-b_lon) * 85)

def risk_assessment(severity, description):
    text = description.lower()
    score = min(100.0, severity * 16.0 + (25 if any(x in text for x in ("fire", "trapped", "multiple")) else 0))
    level = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 35 else "low"
    return round(score, 2), level

def audit(conn, action, entity_type, entity_id, details):
    conn.execute("INSERT INTO audit_log(action,entity_type,entity_id,details,created_at) VALUES(?,?,?,?,?)",
                 (action, entity_type, entity_id, json.dumps(details), now()))
