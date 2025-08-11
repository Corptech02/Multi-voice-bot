#!/bin/bash
# Generate self-signed SSL certificate for HTTPS

echo "Generating self-signed SSL certificate..."
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 \
    -subj "/C=US/ST=State/L=City/O=ClaudeVoiceBot/CN=192.168.40.232"

echo "Certificate generated!"
echo "Files created:"
echo "  - cert.pem (certificate)"
echo "  - key.pem (private key)"