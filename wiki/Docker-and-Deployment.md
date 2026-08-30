# Docker and Deployment

## Published image

```bash
docker pull ghcr.io/iamrichmack111/speaktrain:v0.6.0
docker run --rm -p 8095:8095 \
  -e SPEAKTRAIN_SECRET_KEY='replace-with-a-long-random-value' \
  -v speaktrain-data:/data \
  ghcr.io/iamrichmack111/speaktrain:v0.6.0
```

The image runs as a non-root user, stores SQLite data in `/data`, exposes `/healthz`, and uses Gunicorn. Tags include the semantic version, major/minor, `latest`, and commit SHA.

## Production notes

- Put TLS and request limits in a reverse proxy.
- Use a strong `SPEAKTRAIN_SECRET_KEY`.
- Back up the `/data` volume.
- Do not expose the Playwright `admin/admin` fixture database; it exists only in isolated tests.
- Piper and Faster Whisper are optional host-side enhancements and are not bundled into the lightweight base image.
