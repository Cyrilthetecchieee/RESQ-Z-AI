import os
import threading
from pathlib import Path
os.environ["RESQ_DB_PATH"] = str(Path(__file__).parent / "test.db")
os.environ["RESQ_SEED"] = "true"

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    db = Path(os.environ["RESQ_DB_PATH"])
    if db.exists(): db.unlink()
    with TestClient(app) as c:
        yield c
    if db.exists(): db.unlink()

def test_seed_and_creation_risk(client):
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/incidents").json()) == 3
    r = client.post("/incidents", json={"title":"New fire","description":"fire and trapped people","latitude":1,"longitude":2,"severity":5})
    assert r.status_code == 201 and r.json()["risk_level"] == "critical"
    assert client.post(f"/incidents/{r.json()['id']}/risk").status_code == 200

def test_validation_and_what_if(client):
    assert client.post("/incidents", json={"title":"","description":"x","latitude":0,"longitude":0,"severity":1}).status_code == 422
    iid = client.get("/incidents").json()[0]["id"]
    result = client.post(f"/incidents/{iid}/what-if", json={"severity":1}).json()
    assert result["baseline_score"] >= result["risk_score"]

def test_compatibility_and_double_booking(client):
    iid = next(x["id"] for x in client.get("/incidents?status=open").json() if x["title"] == "Flooded underpass")
    resources = client.get("/resources").json()
    incompatible = next(r for r in resources if "rescue" not in r["capabilities"])
    payload = {"incident_id":iid,"resource_id":incompatible["id"],"start_at":"2030-01-01T00:00:00Z","end_at":"2030-01-01T01:00:00Z"}
    assert client.post("/allocations", json=payload).status_code == 409
    compatible = next(r for r in resources if "rescue" in r["capabilities"])
    payload["resource_id"] = compatible["id"]
    assert client.post("/allocations", json=payload).status_code == 201
    assert client.post("/allocations", json=payload).status_code == 409

def test_recommendation_decision_audit_metrics(client):
    iid = client.get("/incidents").json()[0]["id"]
    rec = client.get(f"/incidents/{iid}/recommendations")
    assert rec.status_code == 200 and rec.json()
    decision = client.post(f"/recommendations/{iid}/decision", json={"decision":"approve"})
    assert decision.status_code in (200, 409)
    assert client.get("/audit").json()
    assert client.get("/metrics").json()["resources"] == 4

def test_api_prefix_and_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}

def test_incident_coordinate_validation(client):
    payload = {"title": "bad coordinate", "description": "signal", "latitude": 91, "longitude": 0, "severity": 2}
    assert client.post("/incidents", json=payload).status_code == 422

def test_incident_long_text_validation(client):
    payload = {"title": "x", "description": "x" * 2001, "latitude": 0, "longitude": 0, "severity": 2}
    assert client.post("/incidents", json=payload).status_code == 422

def test_critical_fire_classification(client):
    result = client.post("/incidents", json={"title": "warehouse", "description": "fire with trapped people", "latitude": 0, "longitude": 0, "severity": 4}).json()
    assert result["risk_level"] == "critical"

def test_low_risk_classification(client):
    result = client.post("/incidents", json={"title": "check", "description": "routine signal", "latitude": 0, "longitude": 0, "severity": 1}).json()
    assert result["risk_level"] == "low"

def test_risk_reassessment_persists(client):
    incident = client.post("/incidents", json={"title": "risk", "description": "smoke", "latitude": 0, "longitude": 0, "severity": 3}).json()
    assessed = client.post(f"/incidents/{incident['id']}/risk").json()
    stored = client.get(f"/incidents/{incident['id']}").json()
    assert assessed["risk_score"] == stored["risk_score"]

def test_risk_missing_incident(client):
    assert client.post("/incidents/999999/risk").status_code == 404

def test_model_dataset_is_deterministic():
    from ml.train_risk_model import build_dataset
    assert build_dataset(20, 11) == build_dataset(20, 11)

def test_model_dataset_has_both_labels():
    from ml.train_risk_model import build_dataset
    _, labels = build_dataset(200, 7)
    assert set(labels) == {0, 1}

def test_model_holdout_metrics_are_computable():
    from ml.train_risk_model import build_dataset
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import f1_score, precision_score, recall_score
    from sklearn.model_selection import train_test_split
    features, labels = build_dataset()
    train_x, test_x, train_y, test_y = train_test_split(features, labels, test_size=.25, random_state=7, stratify=labels)
    model = RandomForestClassifier(n_estimators=10, random_state=7).fit(train_x, train_y)
    predictions = model.predict(test_x)
    assert all(0 <= metric(test_y, predictions) <= 1 for metric in (precision_score, recall_score, f1_score))

def test_resource_creation_validation(client):
    response = client.post("/resources", json={"name": "", "kind": "team", "capabilities": "medical", "latitude": 0, "longitude": 0})
    assert response.status_code == 422

def test_resource_creation_persists(client):
    response = client.post("/resources", json={"name": "QA Unit", "kind": "vehicle", "capabilities": "rescue", "latitude": 0, "longitude": 0})
    assert response.status_code == 201
    assert any(resource["name"] == "QA Unit" for resource in client.get("/resources").json())

def test_resource_available_filter(client):
    assert all(resource["available"] == 1 for resource in client.get("/resources?available=true").json())

def test_fire_requires_fire_capability(client):
    fire = client.post("/incidents", json={"title": "fire", "description": "fire", "latitude": 0, "longitude": 0, "severity": 5}).json()
    non_fire = next(resource for resource in client.get("/resources").json() if "fire" not in resource["capabilities"])
    payload = {"incident_id": fire["id"], "resource_id": non_fire["id"], "start_at": "2040-01-01T00:00:00Z", "end_at": "2040-01-01T01:00:00Z"}
    assert client.post("/allocations", json=payload).status_code == 409

def test_allocation_updates_availability(client):
    incident = next(item for item in client.get("/incidents").json() if item["title"] == "Flooded underpass")
    resource = next(resource for resource in client.get("/resources").json() if "rescue" in resource["capabilities"] and resource["available"])
    payload = {"incident_id": incident["id"], "resource_id": resource["id"], "start_at": "2041-01-01T00:00:00Z", "end_at": "2041-01-01T01:00:00Z"}
    response = client.post("/allocations", json=payload)
    assert response.status_code == 201
    assert next(item for item in client.get("/resources").json() if item["id"] == resource["id"])["available"] == 0

def test_allocation_rejects_reversed_interval(client):
    incident = client.get("/incidents").json()[0]
    resource = client.get("/resources").json()[0]
    payload = {"incident_id": incident["id"], "resource_id": resource["id"], "start_at": "2042-01-01T01:00:00Z", "end_at": "2042-01-01T00:00:00Z"}
    assert client.post("/allocations", json=payload).status_code == 422

def test_allocation_rejects_missing_entity(client):
    payload = {"incident_id": 999999, "resource_id": 999999, "start_at": "2042-01-01T00:00:00Z", "end_at": "2042-01-01T01:00:00Z"}
    assert client.post("/allocations", json=payload).status_code == 404

def test_recommendations_include_rationale(client):
    incident = client.get("/incidents").json()[0]
    response = client.get(f"/incidents/{incident['id']}/recommendations")
    assert response.status_code == 200
    if response.json():
        assert {"resource_id", "score", "rationale"} <= response.json()[0].keys()

def test_recommendations_missing_incident(client):
    assert client.get("/incidents/999999/recommendations").status_code == 404

def test_rejection_is_recorded(client):
    incident = client.post("/incidents", json={"title": "reject", "description": "signal", "latitude": 0, "longitude": 0, "severity": 2}).json()
    client.get(f"/incidents/{incident['id']}/recommendations")
    response = client.post(f"/recommendations/{incident['id']}/decision", json={"decision": "reject", "reason": "capacity reserved"})
    assert response.status_code == 200 and response.json()["decision"] == "reject"

def test_override_requires_resource(client):
    incident = client.get("/incidents").json()[0]
    assert client.post(f"/recommendations/{incident['id']}/decision", json={"decision": "override"}).status_code == 422

def test_invalid_decision_is_rejected(client):
    incident = client.get("/incidents").json()[0]
    assert client.post(f"/recommendations/{incident['id']}/decision", json={"decision": "dispatch"}).status_code == 422

def test_audit_limit_validation(client):
    assert client.get("/audit?limit=0").status_code == 422

def test_audit_details_are_present(client):
    event = client.get("/audit").json()[0]
    assert event["action"] and event["created_at"]

def test_metrics_shape(client):
    metrics = client.get("/metrics").json()
    assert {"incidents", "open_incidents", "resources", "active_allocations"} <= metrics.keys()

def test_simulation_lifecycle(client):
    assert client.post("/simulation/start").json()["enabled"] is True
    assert client.post("/simulation/pause").json()["enabled"] is False
    assert client.post("/simulation/reset").json()["enabled"] is False

def test_simulation_payload_validation(client):
    assert client.post("/simulation", json={"enabled": "not-bool"}).status_code == 422

def test_database_persistence_across_clients(client):
    incident = client.post("/incidents", json={"title": "persist", "description": "signal", "latitude": 1, "longitude": 1, "severity": 2}).json()
    with TestClient(app) as second_client:
        assert second_client.get(f"/incidents/{incident['id']}").status_code == 200

def test_websocket_connection_event(client):
    with client.websocket_connect("/ws/events") as websocket:
        assert websocket.receive_json()["type"] == "connected"

def test_websocket_receives_incident_event(client):
    with client.websocket_connect("/ws/events") as websocket:
        assert websocket.receive_json()["type"] == "connected"
        response = client.post("/incidents", json={"title": "socket", "description": "signal", "latitude": 1, "longitude": 1, "severity": 2})
        event = websocket.receive_json()
        assert response.status_code == 201 and event["type"] == "incident.created"

def test_concurrent_allocations_have_one_winner(client):
    incident = client.get("/incidents").json()[0]
    resource = next(item for item in client.get("/resources").json() if item["available"])
    payload = {"incident_id": incident["id"], "resource_id": resource["id"], "start_at": "2044-01-01T00:00:00Z", "end_at": "2044-01-01T01:00:00Z"}
    results = []
    def submit():
        with TestClient(app) as local_client:
            results.append(local_client.post("/allocations", json=payload).status_code)
    threads = [threading.Thread(target=submit) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(results) == [201, 409]

def test_concurrent_approvals_have_one_decision(client):
    incident = client.post("/incidents", json={"title": "approval race", "description": "medical emergency", "latitude": 40.71, "longitude": -74.01, "severity": 3}).json()
    assert client.get(f"/incidents/{incident['id']}/recommendations").json()
    results = []
    def approve():
        with TestClient(app) as local_client:
            results.append(local_client.post(f"/recommendations/{incident['id']}/decision", json={"decision": "approve"}).status_code)
    threads = [threading.Thread(target=approve) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(results) == [200, 404]
