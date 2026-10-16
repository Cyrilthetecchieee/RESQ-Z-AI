# API reference

The root paths below also accept the `/api` prefix.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Backend health |
| GET | `/incidents` | List incidents, optionally `?status=open` |
| POST | `/incidents` | Create and score a simulated incident |
| GET | `/incidents/{id}` | Fetch one incident |
| POST | `/incidents/{id}/risk` | Recalculate risk |
| GET | `/incidents/{id}/recommendations` | Rank compatible available resources |
| POST | `/incidents/{id}/what-if` | Compare an alternative severity/description |
| GET | `/resources` | List resources, optionally `?available=true` |
| POST | `/resources` | Add a resource |
| POST | `/allocations` | Create an overlap-protected allocation |
| POST | `/recommendations/{id}/decision` | Approve, reject, or override |
| GET | `/audit?limit=100` | Read recent audit events |
| GET | `/metrics` | Operational counters |
| POST | `/simulation/start` | Enable simulation |
| POST | `/simulation/pause` | Pause simulation |
| POST | `/simulation/reset` | Reset simulation state |
| WS | `/ws/events` | Incident/allocation notifications |

All inputs are Pydantic-validated. Invalid coordinates, severity, required text,
date ranges, and override resource selection return a meaningful 422. Missing
entities return 404; incompatible or double-booked resources return 409.
