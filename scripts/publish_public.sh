#!/usr/bin/env bash
set -euo pipefail

owner="${SPEAKTRAIN_GITHUB_OWNER:-iamrichmack111}"
repository="${SPEAKTRAIN_GITHUB_REPOSITORY:-SpeakTrain}"
version="${SPEAKTRAIN_RELEASE_TAG:-v0.6.0}"
slug="${owner}/${repository}"
description="Adaptive Spanish and Syrian Arabic speaking trainer with local speech scoring, spaced repetition, Docker, Playwright, and D2."

for command_name in git gh ssh; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Required command not found: ${command_name}" >&2
    exit 1
  fi
done

gh auth status
gh config set git_protocol ssh

if ! ssh-add -L >/dev/null 2>&1; then
  echo "No SSH key is loaded. Run: ssh-add --apple-use-keychain ~/.ssh/id_ed25519" >&2
  exit 1
fi

if ! gh repo view "${slug}" >/dev/null 2>&1; then
  gh repo create "${slug}" --public --description "${description}" --enable-issues
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "git@github.com:${slug}.git"
else
  git remote add origin "git@github.com:${slug}.git"
fi

gh repo edit "${slug}" \
  --description "${description}" \
  --homepage "https://github.com/${slug}" \
  --enable-issues \
  --enable-wiki \
  --visibility public \
  --accept-visibility-change-consequences

for topic in flask language-learning spanish arabic whisper spaced-repetition playwright docker d2; do
  gh repo edit "${slug}" --add-topic "${topic}"
done

git push --set-upstream origin main
git push origin "${version}"

echo
echo "Published https://github.com/${slug}"
echo "The ${version} tag starts the GHCR multi-architecture image workflow."
echo "After creating the first Wiki page on GitHub, run scripts/publish_wiki.sh."
