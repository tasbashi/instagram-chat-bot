#!/usr/bin/env bash
set -euo pipefail

# ══════════════════════════════════════════════════════════════
#  Instagram Chatbot — EC2 Deploy Script
#  Run on a fresh Ubuntu 22.04+ EC2 instance
# ══════════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════"
echo "  📦 Instagram Chatbot — EC2 Deployment"
echo "════════════════════════════════════════════════"

# ── 1. Install Docker + Compose ──
if ! command -v docker &>/dev/null; then
    echo "🔧 Installing Docker..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker "$USER"
    echo "✅ Docker installed"
else
    echo "✅ Docker already installed"
fi

# ── 2. Check .env ──
if [ ! -f backend/.env ]; then
    echo ""
    echo "⚠️  No backend/.env found!"
    echo "   Copy .env.production.template → backend/.env and fill in your secrets."
    echo "   Then re-run this script."
    echo ""
    exit 1
fi

# ── 3. Build & Start ──
echo ""
echo "🚀 Building and starting services..."
sudo docker compose up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 5

# ── 5. Status ──
echo ""
sudo docker compose ps
echo ""

# Check backend health
if curl -sf http://localhost/health > /dev/null 2>&1; then
    echo "✅ Backend: healthy"
else
    echo "⚠️  Backend: not responding yet (may still be starting)"
fi

SERVER_IP=$(curl -s --max-time 3 http://checkip.amazonaws.com 2>/dev/null || echo "63.182.241.50")

echo ""
echo "════════════════════════════════════════════════"
echo "  🎉 Deployment complete!"
echo ""
echo "  🌐 Frontend: http://${SERVER_IP}"
echo "  📡 API:      http://${SERVER_IP}/api/"
echo "  🪝 Webhook:  Check backend logs for ngrok URL"
echo ""
echo "  📋 Useful commands:"
echo "     sudo docker compose logs -f backend   # Backend logs"
echo "     sudo docker compose logs -f nginx     # Nginx logs"
echo "     sudo docker compose restart backend   # Restart backend"
echo "     sudo docker compose down              # Stop all"
echo "     sudo docker compose up -d --build     # Rebuild & start"
echo "════════════════════════════════════════════════"
