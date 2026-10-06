#!/usr/bin/env bash
# Start the site for students.
#   ADMIN_PASSWORD='...' ./run.sh            -> local network link (same Wi-Fi)
#   ADMIN_PASSWORD='...' ./run.sh --tunnel   -> also a public https link (needs cloudflared + internet)
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-5000}"
: "${ADMIN_PASSWORD:?Set it first, e.g.  ADMIN_PASSWORD='mot-de-passe' ./run.sh}"
export ADMIN_PASSWORD
export SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

[ -d .venv ] || { uv venv && uv pip install -r requirements.txt; }

show() {  # print a link, plus a QR code students can scan if qrencode is installed
  echo; echo "  👉  $1"; echo
  if command -v qrencode >/dev/null; then qrencode -t ansiutf8 "$1"; fi
}

IP=$(ip -4 -o addr show scope global | awk '{print $4}' | cut -d/ -f1 | head -1)
echo "=============================================="
echo " Lien réseau local (même Wi-Fi) :"
show "http://$IP:$PORT"
echo " Admin : http://$IP:$PORT/admin"
echo "=============================================="

if [ "${1:-}" = "--tunnel" ]; then
  command -v cloudflared >/dev/null || { echo "cloudflared missing: sudo pacman -S cloudflared"; exit 1; }
  cloudflared tunnel --url "http://localhost:$PORT" 2> .tunnel.log &
  trap 'kill $! 2>/dev/null' EXIT
  echo "Création du lien public…"
  URL=""
  for _ in $(seq 30); do
    URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' .tunnel.log | head -1 || true)
    [ -n "$URL" ] && break
    sleep 1
  done
  if [ -n "$URL" ]; then
    echo " Lien public (marche partout, même en 4G) :"; show "$URL"
  else
    echo "⚠️  Tunnel failed, see .tunnel.log. The local link above still works."
  fi
fi

echo "Serveur lancé. Ctrl+C pour arrêter."
.venv/bin/gunicorn -w 2 -b "0.0.0.0:$PORT" --access-logfile - app:app
