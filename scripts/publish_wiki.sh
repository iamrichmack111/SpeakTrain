#!/usr/bin/env bash
set -euo pipefail

owner="${SPEAKTRAIN_GITHUB_OWNER:-iamrichmack111}"
repository="${SPEAKTRAIN_GITHUB_REPOSITORY:-SpeakTrain}"
slug="${owner}/${repository}"
temporary_directory="$(mktemp -d)"

cleanup() {
  rm -rf "${temporary_directory}"
}
trap cleanup EXIT

if ! command -v gh >/dev/null 2>&1; then
  echo "Required command not found: gh" >&2
  exit 1
fi

gh auth status
gh config set git_protocol ssh

if ! git clone "git@github.com:${slug}.wiki.git" "${temporary_directory}/wiki"; then
  echo "Open https://github.com/${slug}/wiki, create its first page, then rerun this command." >&2
  exit 1
fi

find "${temporary_directory}/wiki" -maxdepth 1 -type f -name '*.md' -delete
cp wiki/*.md "${temporary_directory}/wiki/"
git -C "${temporary_directory}/wiki" add --all

if git -C "${temporary_directory}/wiki" diff --cached --quiet; then
  echo "Wiki is already current."
  exit 0
fi

git -C "${temporary_directory}/wiki" commit -m "docs: publish SpeakTrain wiki"
git -C "${temporary_directory}/wiki" push origin master
echo "Published https://github.com/${slug}/wiki"
