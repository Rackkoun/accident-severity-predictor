#!/bin/bash
# Generate self-signed certificate for development
# Usage: ./infra/nginx/generate-dev-cert.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="${SCRIPT_DIR}/certs"

echo "Generating self-signed certificate for asp.local..."

# Generate private key
openssl genrsa -out "${CERT_DIR}/nginx.key" 2048

# Generate certificate request
openssl req -new -key "${CERT_DIR}/nginx.key" -out "${CERT_DIR}/nginx.csr" \
  -subj "/CN=asp.local/O=Development/C=DE"

# Generate self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in "${CERT_DIR}/nginx.csr" \
  -signkey "${CERT_DIR}/nginx.key" -out "${CERT_DIR}/nginx.crt"

# Cleanup CSR file (not needed after certificate generation)
rm -f "${CERT_DIR}/nginx.csr"

echo "Certificate generated successfully!"
echo "Location: ${CERT_DIR}/nginx.crt"
echo "Private key: ${CERT_DIR}/nginx.key"
echo ""
echo "Note: This is a self-signed certificate. Your browser will show a security warning."
echo "To use HTTPS locally, add to /etc/hosts:"
echo "  127.0.0.1 asp.local"
