# Security Policy

## Supported version

Security fixes target the latest tagged release.

## Report a vulnerability

Use GitHub’s private vulnerability reporting for this repository. Do not open a public issue containing exploit details, credentials, personal learning records, or database contents.

## Deployment requirements

- Replace `SPEAKTRAIN_SECRET_KEY` with a long random value.
- Terminate TLS at a trusted reverse proxy.
- Protect and back up the SQLite volume.
- Keep `instance/`, `.env`, recordings, speech models, and Playwright fixtures out of Git.
- Never deploy the `admin/admin` Playwright database.
- Apply operating-system and dependency updates.

SpeakTrain is designed for trusted local or small private deployments. Review authentication, CSRF protection, rate limiting, database choice, and backup strategy before exposing it to untrusted internet traffic.
