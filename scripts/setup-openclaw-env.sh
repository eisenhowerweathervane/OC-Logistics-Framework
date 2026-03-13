#!/usr/bin/env bash
# setup-openclaw-env.sh — OC Logistics Phase 3 setup helper
#
# Run once after the backend is up and seeded:
#   bash scripts/setup-openclaw-env.sh
#
# What this does:
#   1. Gets a JWT token for the owner account
#   2. Writes OC_BACKEND_URL and OC_BACKEND_TOKEN to ~/.oc-logistics-env
#   3. Prints instructions to source it from ~/.zshrc

set -euo pipefail

BACKEND_URL="${OC_BACKEND_URL:-http://localhost:8000}"
ENV_FILE="$HOME/.oc-logistics-env"

echo "🔐 OC Logistics — OpenClaw env setup"
echo "Backend: $BACKEND_URL"
echo ""

read -rp "Owner email: " EMAIL
read -rsp "Password: " PASSWORD
echo ""

RESPONSE=$(curl -s -X POST "$BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || true)

if [[ -z "$ACCESS_TOKEN" ]]; then
  echo "❌ Login failed. Response:"
  echo "$RESPONSE"
  exit 1
fi

cat > "$ENV_FILE" <<EOF
# OC Logistics — backend credentials for OpenClaw plugin
export OC_BACKEND_URL="$BACKEND_URL"
export OC_BACKEND_TOKEN="$ACCESS_TOKEN"
EOF

chmod 600 "$ENV_FILE"

echo "✅ Token saved to $ENV_FILE"
echo ""
echo "Add this to your ~/.zshrc (if not already there):"
echo "  source $ENV_FILE"
echo ""
echo "Then restart the OpenClaw gateway:"
echo "  openclaw daemon restart"
