#!/usr/bin/env bash
# Genera el par de llaves RSA asimétricas usadas para firmar (privada) y
# verificar (pública) los JWT emitidos por el backend (algoritmo RS256).
set -euo pipefail

KEYS_DIR="${1:-backend/keys}"
mkdir -p "$KEYS_DIR"

openssl genrsa -out "$KEYS_DIR/private.pem" 2048
openssl rsa -in "$KEYS_DIR/private.pem" -pubout -out "$KEYS_DIR/public.pem"

echo "Llaves generadas en $KEYS_DIR/ (private.pem, public.pem)"
echo "IMPORTANTE: agregue $KEYS_DIR/private.pem a .gitignore — nunca debe versionarse."
