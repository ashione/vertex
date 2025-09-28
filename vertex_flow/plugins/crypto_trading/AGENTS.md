# Repository Guidelines

## Project Structure & Module Organization
- `client.py`: main entry for exchange operations; keep orchestration here.
- `trading.py`: trading engine plus risk helpers reused by demos.
- `exchanges.py`: adapter base classes and OKX/Binance clients; extend for new venues.
- `config.py`: dataclasses for credentials, risk defaults, and feature flags.
- `execution_controls.py`, `risk_manager.py`, `monitoring.py`: execution limits, risk checks, and alert fan-out.
- `scheduler.py`, `backtester.py`: reusable automation hooks and reference strategies for simulations.
- `persistence.py`: JSONL datastore for trades, metrics, configs.
- `indicators.py`, `position_metrics.py`: analytics utilities; add metrics here to stay reusable.
- Scripts `example.py` and `show_indicators.py` demonstrate workflows; keep CLI experiments separate from library code.
- Plan future tests in `tests/` mirroring module names (for example, `tests/test_trading.py`).

## Setup, Build & Run
- `python3 -m venv .venv && source .venv/bin/activate` isolates dependencies.
- `pip install -r requirements.txt` installs exchange SDKs, TA libraries, and logging deps.
- `python example.py` runs a full account→signal→trade sample.
- `python show_indicators.py` prints OKX positions with indicator summaries; mock network calls when offline.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation, snake_case functions, and PascalCase classes.
- Keep modules typed and mirror the concise docstrings used in `client.py`.
- Order imports as stdlib / third-party / local and keep them alphabetical.
- Surface reusable constants in `config.py` or clearly named enums instead of magic literals.

## Testing Guidelines
- Prefer `pytest`; stage fixtures in `tests/conftest.py` so exchange mocks and timestamps are shared.
- Name tests `test_<behavior>` and focus on deterministic paths by stubbing HTTP clients.
- Cover branch-heavy risk logic in `trading.py` and adapter fallbacks in `exchanges.py`.
- Document the exact `pytest` invocation and result in every PR.

## Commit & Pull Request Guidelines
- Match existing history: `<type>: <short summary>` (`fix: adjust fee rounding`, `lint`).
- Keep subjects ≤72 chars; explain config or data contract changes in the body.
- Reference related issues with `(#123)` and call out manual test commands in the PR description.
- PRs should outline intent, risk, and screenshots or console snippets when behavior shifts.

## Security & Configuration Tips
- Secrets live in `.env`; never check concrete keys into the repo or fixtures.
- Default to sandbox credentials (`sandbox=True`) during manual runs and signal when production access is required.
- Sanitize recorded responses before storing them in tests or logs.
