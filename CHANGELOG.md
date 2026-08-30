# Changelog

All notable changes to SpeakTrain are documented here.

## [0.6.1] - 2026-08-30

### Fixed

- **Faster Whisper missing from the default release**
  - Problem: SpeakTrain started successfully, but speech recognition displayed `faster-whisper is not installed`.
  - Cause: `faster-whisper` was only listed in `requirements-speech.txt`, while the standard installation and Docker image installed only `requirements.txt`.
  - Resolution: Promoted Faster Whisper and its required HTTP dependency into the default installation path.
  - Result: Local installs and the GHCR `latest` container now include speech-recognition support by default.

- **Playwright authentication failed in CI**
  - Problem: Documentation screenshot tests could load `/login` but repeatedly timed out attempting to authenticate.
  - Cause: The browser test depended on login-button markup and UI form submission behavior.
  - Resolution: Authentication now uses the isolated Playwright test database and a direct `/login` request that shares the browser session cookie.
  - Result: The screenshot suite authenticates deterministically without exposing or using production credentials.

- **Phrase Practice screenshot test was unstable**
  - Problem: The phrase text loaded, but Playwright reported `#target` as hidden.
  - Cause: The asynchronous catalog render completed before the Practice view had reliably become active.
  - Resolution: The test waits for populated practice data, activates the exact `data-view="practice"` tab, and verifies the view is active before taking the screenshot.
  - Result: The full Playwright suite passes locally and in GitHub Actions.

- **Flask dependency security advisory**
  - Problem: `pip-audit` detected `PYSEC-2026-2151` against Flask 3.1.2.
  - Resolution: Upgraded Flask to 3.1.3.
  - Result: Dependency auditing passes.

- **D2 documentation rendering failed**
  - Problem: CI rejected the old `border-radius` syntax.
  - Resolution: Updated diagrams to use `style.border-radius`.
  - Result: README/Wiki/D2 validation renders successfully.

### CI/CD

- CI passes on `main`.
- CodeQL passes on `main`.
- Documentation screenshot workflow passes.
- Playwright health and protected-route tests pass.
- GHCR container publishing succeeds.
- Docker `latest` was rebuilt from the corrected source.
- Public Wiki is initialized and synchronized.

### Security / Test Isolation

- `admin/admin` remains restricted to the isolated Playwright test database.
- Git operations use the SSH repository remote.
- Production credentials are not embedded in the Playwright workflow.

## [0.6.0] - 2026-08-30

### Added

- Initial public SpeakTrain release.
- Flask application and language-learning interface.
- Spanish and Arabic learning content.
- Phrase practice and speech scoring.
- OPI simulator.
- Vocabulary recall.
- Conjugation drills.
- Guided conversation.
- Vocabulary and sentence laboratory.
- Progress and mastery tracking.
- Administrative curriculum tools.
- Weekly reports.
- Playwright documentation screenshots.
- D2 architecture documentation.
- GitHub Actions CI and CodeQL.
- Dependabot.
- Docker and GHCR publishing.
- GitHub Wiki publishing.

### Release Infrastructure

- Public repository: `iamrichmack111/SpeakTrain`
- Container registry: `ghcr.io/iamrichmack111/speaktrain`
- Initial container release: `v0.6.0`
