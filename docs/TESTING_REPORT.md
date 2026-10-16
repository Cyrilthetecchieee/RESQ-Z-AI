# Testing report

The backend test suite covers seeded startup, validated incident creation,
risk scoring, what-if comparisons, capability compatibility, overlapping
allocation rejection, recommendation decisions, audit events, and metrics.
The frontend build runs TypeScript checking followed by Vite production
bundling.

Run:

```powershell
pytest
npm run build
```

The prototype test suite is not a substitute for load, security, accessibility,
browser compatibility, or emergency-service certification testing. WebSocket
coverage should be expanded as the simulation engine becomes asynchronous.

## Current evidence

The expanded backend suite contains **36 meaningful tests** covering validation,
risk classification, deterministic dataset behavior, holdout metrics, resource
compatibility, allocation persistence, availability changes, recommendations,
decisions, audit, lifecycle controls, database persistence, WebSocket events,
and concurrent allocation serialization. The latest run was:

```text
36 passed, 1 warning in 6.01s
```

The warning is a Starlette/httpx deprecation warning from the installed local
test stack. It does not fail the suite.

Repeatable local development measurements (20 requests per endpoint, Windows
development machine, TestClient, not LinuxONE performance) were:

| Operation | Mean | P95 |
|---|---:|---:|
| Health | 2.364 ms | 4.260 ms |
| Incident list | 3.949 ms | 5.510 ms |
| Risk reassessment | 29.076 ms | 39.456 ms |
| Recommendation generation | 29.142 ms | 36.562 ms |

The UI TypeScript/Vite build also passes. Browser-level responsive,
accessibility, and multi-page interaction testing remain manual follow-ups.
