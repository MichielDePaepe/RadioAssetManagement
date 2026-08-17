#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <host> <ip> [extra-dns-or-ip ...]"
  echo "Example: $0 ram.local 192.168.20.50 radioasset.local"
  exit 1
fi

HOST="$1"
shift

CERT_DIR="${CERT_DIR:-./certs}"
CA_KEY="$CERT_DIR/ram-lan-ca.key"
CA_CRT="$CERT_DIR/ram-lan-ca.crt"
SERVER_KEY="$CERT_DIR/ram-lan.key"
SERVER_CSR="$CERT_DIR/ram-lan.csr"
SERVER_CRT="$CERT_DIR/ram-lan.crt"
OPENSSL_CNF="$CERT_DIR/ram-lan.openssl.cnf"

mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

if [ ! -f "$CA_KEY" ] || [ ! -f "$CA_CRT" ]; then
  openssl genrsa -out "$CA_KEY" 4096
  openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days 3650 \
    -out "$CA_CRT" \
    -subj "/CN=Radio Asset Management LAN CA"
fi

cat > "$OPENSSL_CNF" <<EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
CN = $HOST

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = $HOST
EOF

dns_index=2
ip_index=1
for name in "$@"; do
  if [[ "$name" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "IP.$ip_index = $name" >> "$OPENSSL_CNF"
    ip_index=$((ip_index + 1))
  else
    echo "DNS.$dns_index = $name" >> "$OPENSSL_CNF"
    dns_index=$((dns_index + 1))
  fi
done

openssl genrsa -out "$SERVER_KEY" 2048
openssl req -new -key "$SERVER_KEY" -out "$SERVER_CSR" -config "$OPENSSL_CNF"
openssl x509 -req -in "$SERVER_CSR" -CA "$CA_CRT" -CAkey "$CA_KEY" \
  -CAcreateserial -out "$SERVER_CRT" -days 825 -sha256 \
  -extensions req_ext -extfile "$OPENSSL_CNF"

chmod 600 "$CA_KEY" "$SERVER_KEY"

echo "Created:"
echo "  CA certificate:     $CA_CRT"
echo "  Server certificate: $SERVER_CRT"
echo "  Server key:         $SERVER_KEY"
echo
echo "Install the CA certificate on each scanner/client PC as a trusted root:"
echo "  $CA_CRT"
