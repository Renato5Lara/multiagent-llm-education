#!/bin/bash
# ============================================================
# setup.sh — Script de despliegue para UPAO-MAS-EDU Backend
# Uso: bash setup.sh
# ============================================================

set -e

echo "============================================"
echo "  UPAO-MAS-EDU — Setup de Producción"
echo "============================================"

# 1. Variables de entorno
if [ ! -f .env ]; then
    echo "[!] No existe .env — copiando desde .env.example"
    cp .env.example .env
    echo "[!] EDITAR .env con los valores de producción antes de continuar"
    exit 1
fi

# 2. Directorios de uploads
echo "[OK] Creando directorios de uploads..."
mkdir -p uploads/courses uploads/resources uploads/images uploads/temp

# 3. Dependencias
echo "[OK] Instalando dependencias..."
pip install -r requirements.txt

# 4. Migraciones
echo "[OK] Ejecutando migraciones..."
alembic upgrade head

# 5. Seed
echo "[OK] Ejecutando seed..."
python seed.py

# 6. Iniciar servidor
echo "============================================"
echo "  Setup completado exitosamente"
echo "============================================"
echo ""
echo "Para iniciar el servidor:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo ""
