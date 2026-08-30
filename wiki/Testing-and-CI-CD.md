# Testing and CI/CD

## Local validation

```bash
pytest -q
npm ci
npx playwright install chromium
PYTHON_EXECUTABLE=.venv/bin/python npm run test:e2e
python scripts/check_docs.py
docker build -t speaktrain:local .
```

## GitHub Actions

- Python tests on 3.10, 3.12, and 3.13.
- Playwright Chromium tests with isolated `admin/admin` login.
- Twelve documentation screenshots and an HTML browser report.
- README, Wiki, screenshot, and D2-icon validation.
- D2 diagram rendering.
- Docker build validation.
- CodeQL for Python and JavaScript.
- `pip-audit` and `npm audit` dependency checks.
- Dependabot for pip, npm, Actions, and Docker.
- Multi-architecture GHCR publish with provenance on semantic-version tags.

The screenshot workflow commits refreshed PNGs with `[skip ci]` to avoid a workflow loop.
