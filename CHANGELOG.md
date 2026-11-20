# Changelog

## 0.1.0 — 2026-11-20

First release, built on the operation list the Jotform API documentation page loads (request-models.js, downloaded 2026-11-20, SHA-256 `ded079d796ecde08f097af8845a409d6afdd8af3f4ad6023f3827af01c51b0a3`).

- 52 operations of the documentation's 56 are steps: forms, questions and properties, submissions, webhooks, reports, labels, folders, the account and its settings. Signing in and out and two operations whose documentation contradicts itself are left out (see Coverage).
- Everyday steps: Test connection, Check readiness, Build support report, List forms, Describe form questions, Get form submissions since, Get submission answers, Create submission, Download submission file, List form webhooks, Add webhook if new and Remove webhook.
- Connections are a Jotform API key and the account's region: standard, EU or HIPAA.
- Changes are sent once and never retried automatically; test runs never send them.
- Get form submissions since builds next_after_ids from its own read of the latest second (every page of it), so the cursor holds every submission of that second however many runs read the window; if that read fails the run is not complete and the cursor stays.
- max_records holds for the first page too: each page asks at most the records still wanted.
