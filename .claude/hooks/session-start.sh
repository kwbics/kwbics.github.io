#!/bin/bash
set -euo pipefail

# Only run in Claude Code cloud (remote) sessions.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Ruby gems (Jekyll + plugins) — installed locally so the container cache keeps them.
bundle config set --local path vendor/bundle
bundle install --jobs 4

# Node tooling (prettier, style-contract lint). npm install benefits from container caching.
npm install --no-audit --no-fund

# Jekyll/al_folio_core needs a UTF-8 locale (Korean content), and Python deps stay optional.
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo 'export LANG=C.UTF-8' >> "$CLAUDE_ENV_FILE"
  echo 'export LC_ALL=C.UTF-8' >> "$CLAUDE_ENV_FILE"
fi
