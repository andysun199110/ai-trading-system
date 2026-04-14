# Architecture Overview

- MT5 EA is execution-only client.
- FastAPI gateway serves client + admin APIs.
- PostgreSQL stores licensing, sessions, audits, signal lifecycle, ops records.
- Redis is optional for cache/queue in future stages.
- Strategy services are isolated modules with stage-1 stubs.
