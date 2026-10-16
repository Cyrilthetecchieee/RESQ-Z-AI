# Architecture

RESQ-Z AI is a deliberately small, portable prototype:

* **Frontend:** Vite + React + TypeScript. The UI uses Recharts and Lucide
  icons. The incident map is a dependency-free schematic so the demo remains
  usable offline; it is not a GIS or routing product.
* **Backend:** FastAPI and Uvicorn expose REST resources and a native
  WebSocket event hub. `/api/*` is accepted through a compatibility middleware
  while the root routes remain available for direct API testing.
* **Persistence:** SQLite with foreign keys enabled. Seed data is deterministic
  and contains three incidents plus four resources.
* **Decision services:** feature-based risk scoring, distance-aware compatible
  resource ranking, interval overlap protection, and explicit operator decision
  endpoints.
* **Audit:** all creation, assessment, allocation, and decision operations
  append an audit event in the same SQLite transaction.

The browser never dispatches automatically. An operator must approve or override
a recommendation before an allocation is created. Travel times and all
incidents are simulated.

## Request flow

1. Incident creation validates coordinates, severity, and text.
2. The risk service computes a score and urgency level.
3. A recommendation ranks available compatible resources by capability and
   estimated distance.
4. The operator approves, rejects, or overrides the recommendation.
5. Allocation checks the resource interval again inside a transaction and emits
   a WebSocket event.
