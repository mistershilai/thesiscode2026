#!/bin/bash
# Add Nginx reverse proxy + Let's Encrypt SSL for a domain.
# Usage: sudo bash deploy/ssl.sh yourdomain.com

set -euo pipefail

DOMAIN="${1:?Usage: sudo bash deploy/ssl.sh yourdomain.com}"

echo "=== Installing Nginx and Certbot ==="
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

echo "=== Configuring Nginx ==="
cat > /etc/nginx/sites-available/kaelo <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support (if needed later)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        # Large file uploads (template uploads)
        client_max_body_size 20M;
    }
}
EOF

ln -sf /etc/nginx/sites-available/kaelo /etc/nginx/sites-enabled/kaelo
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "=== Obtaining SSL certificate ==="
certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos --register-unsafely-without-email

echo ""
echo "============================================"
echo "  HTTPS is live at https://${DOMAIN}"
echo "  Certificate auto-renews via certbot timer."
echo "============================================"
