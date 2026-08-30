# Contributing to SpeakTrain

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm ci
npx playwright install chromium
```

Create a branch, keep commits focused, and run:

```bash
pytest -q
PYTHON_EXECUTABLE=.venv/bin/python npm run test:e2e
python scripts/check_docs.py
```

Visible changes require refreshed Playwright screenshots. Curriculum changes should include transliteration, gender/register notes where applicable, and tests.

## Publish the repository Wiki

After the public repository exists and Wiki is enabled, confirm SSH access with `ssh -T git@github.com` and then publish:

```bash
git clone git@github.com:iamrichmack111/SpeakTrain.wiki.git
cp wiki/*.md SpeakTrain.wiki/
cd SpeakTrain.wiki
git add .
git commit -m "docs: publish complete SpeakTrain wiki"
git push origin HEAD
```

## Pull requests

- Explain learner impact and migration behavior.
- Link an issue where possible.
- Keep test fixtures isolated from real `instance/` data.
- Never commit accounts, databases, speech recordings, models, or secrets.
