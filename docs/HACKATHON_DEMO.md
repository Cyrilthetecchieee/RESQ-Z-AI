# Hackathon demonstration

1. Start the backend and frontend.
2. Open Command Center and confirm the seeded incident/resource view.
3. Run and pause the synthetic simulation controls; the UI remains explicit
   about demo mode when a backend WebSocket is unavailable.
4. Create a road collision, fire, or medical incident with the manual form.
5. Open Incident Intelligence and compare the risk level and contributing
   hazard signal.
6. In Decision Lab, compare alternative assignments conceptually, then approve
   or reject a recommendation. No dispatch occurs automatically.
7. Open Resource Command to show availability and allocation impact.
8. Open Audit Center to show the recorded decision trail and System
   Intelligence to show health/metrics.

The scenario is repeatable because the seed data and model features are
deterministic. Locations, response times, and outcomes are simulated estimates,
not live traffic, medical, or public-safety predictions.

## Known demo limitations

The current `/simulation/start` and `/simulation/pause` endpoints control
simulation state but do not yet run a background incident generator. The
repeatable three-incident story is therefore performed with seeded/manual
incidents and the explicit UI controls. A production-like demo still needs an
asynchronous scheduler and a reset transaction that restores the seed state.
