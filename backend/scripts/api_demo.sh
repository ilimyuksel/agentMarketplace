#!/usr/bin/env bash
# Quick curl-based tour of the REST API.
#
# Prereqs:
#   1. docker compose up -d     (postgres + redis)
#   2. uvicorn backend.main:app --port 8000 &
#
# Usage:
#   ./scripts/api_demo.sh
#
# Frontend teammates: this script is the canonical reference for the
# request/response envelopes you'll be binding to.

set -euo pipefail

API="${API:-http://localhost:8000/api/v1}"

# Pretty-print JSON if jq is available; otherwise fall back to raw output.
if command -v jq >/dev/null 2>&1; then
  PP="jq ."
  PP_RAW="jq -r"
else
  echo "[hint] install \`jq\` for pretty output" >&2
  PP="cat"
  PP_RAW="cat"
fi

hdr() { printf '\n\033[1;34m=== %s ===\033[0m\n' "$1"; }

hdr "GET ${API}/health"
curl -fsS "${API}/health" | eval "$PP"

hdr "GET ${API}/stats"
curl -fsS "${API}/stats" | eval "$PP"

hdr "GET ${API}/agents"
curl -fsS "${API}/agents" | eval "$PP" | head -60

hdr "POST ${API}/ledger/verify (the demo's 'trust button')"
curl -fsS -X POST "${API}/ledger/verify" | eval "$PP"

hdr "GET ${API}/ledger/recent?limit=5"
curl -fsS "${API}/ledger/recent?limit=5" | eval "$PP"

hdr "GET ${API}/wallets"
curl -fsS "${API}/wallets" | eval "$PP" | head -60

hdr "POST ${API}/jobs"
RESPONSE=$(curl -fsS -X POST "${API}/jobs" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a landing page for a developer AI tool", "budget": 200.00}')
echo "$RESPONSE" | eval "$PP"

JOB_ID=$(echo "$RESPONSE" | eval "${PP_RAW} .data.job_id")
echo "[hint] subscribe to: ws://localhost:8000/ws/jobs/${JOB_ID}"

hdr "GET ${API}/jobs/${JOB_ID}"
curl -fsS "${API}/jobs/${JOB_ID}" | eval "$PP"

hdr "GET ${API}/jobs"
curl -fsS "${API}/jobs?limit=5" | eval "$PP" | head -40

echo
echo "[done] all endpoints responded."
