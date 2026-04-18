#!/bin/bash
# Oracle Cloud Free Tier — Kaelo deployment script
# Run this on a fresh Oracle Cloud ARM VM (Ampere A1, Ubuntu 22.04+)
#
# Prerequisites:
#   1. Create an Oracle Cloud account (always-free tier)
#   2. Launch an Ampere A1 VM: 4 OCPU / 24GB RAM / Ubuntu 22.04
#   3. Open ingress ports 80, 443, 8000 in the VCN security list
#   4. SSH into the VM and run: bash setup.sh
#
# After setup, the app will be at http://<your-vm-ip>:8000
# (or https://<your-domain> if you configure the Nginx + Certbot step)

set -euo pipefail

echo "=== 1/5  Installing Docker ==="
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
echo "Docker installed. You may need to log out and back in for group permissions."

echo ""
echo "=== 2/5  Cloning repo ==="
if [ ! -d "$HOME/kaelo" ]; then
  git clone https://github.com/elee/thesiscode2026.git "$HOME/kaelo"
else
  echo "Repo already exists at ~/kaelo — pulling latest"
  cd "$HOME/kaelo" && git pull
fi
cd "$HOME/kaelo"

echo ""
echo "=== 3/5  Preparing OSRM data ==="
# OSRM needs pre-processed Botswana road data.
# If osrm_project/botswana-latest.osrm doesn't exist, download and process it.
if [ ! -f osrm_project/botswana-latest.osrm ]; then
  echo "Downloading Botswana OSM extract and processing for OSRM..."
  mkdir -p osrm_project && cd osrm_project
  curl -L -o botswana-latest.osm.pbf https://download.geofabrik.de/africa/botswana-latest.osm.pbf
  docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 \
    osrm-extract -p /opt/car.lua /data/botswana-latest.osm.pbf
  docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 \
    osrm-partition /data/botswana-latest.osrm
  docker run --rm -v "$(pwd):/data" ghcr.io/project-osrm/osrm-backend:v5.27.1 \
    osrm-customize /data/botswana-latest.osrm
  cd ..
  echo "OSRM data ready."
else
  echo "OSRM data already exists — skipping."
fi

echo ""
echo "=== 4/5  Building and starting containers ==="
docker compose up -d --build

echo ""
echo "=== 5/5  Verifying ==="
sleep 10
if curl -sf http://localhost:8000/api/health > /dev/null; then
  echo ""
  echo "============================================"
  echo "  Kaelo is running!"
  echo "  http://$(curl -s ifconfig.me):8000"
  echo "============================================"
else
  echo "Health check failed — check logs with: docker compose logs"
fi

echo ""
echo "Optional next steps:"
echo "  - Point a domain to this VM's IP"
echo "  - Run: sudo bash deploy/ssl.sh your-domain.com"
echo "  - This adds Nginx + free Let's Encrypt HTTPS"
