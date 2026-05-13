#!/usr/bin/env bash
# install_cron.sh — Installe les 3 entrées crontab pour CryptoLascar (D-02).
# Usage : bash scheduler/install_cron.sh
# Prérequis : timedatectl set-timezone Europe/Paris (D-04)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$(command -v python3)"

# Entrées crontab D-02 exactes
CRON_DAILY="0 7 * * 1-6   cd $PROJECT_DIR && $PYTHON main.py --mode daily"
CRON_WEEKLY="0 8 * * 0     cd $PROJECT_DIR && $PYTHON main.py --mode weekly"
CRON_MONTHLY="0 8 * * *     cd $PROJECT_DIR && $PYTHON main.py --mode monthly"

# Vérification idempotente — ne pas installer si déjà présent
if crontab -l 2>/dev/null | grep -q "$PROJECT_DIR"; then
    echo "Crontab entries already installed — skipping."
    echo ""
    echo "Crontab actuel :"
    crontab -l
    exit 0
fi

# Installation des 3 entrées
(crontab -l 2>/dev/null || true; echo "# CryptoLascar — rapports financiers automatisés"; echo "$CRON_DAILY"; echo "$CRON_WEEKLY"; echo "$CRON_MONTHLY") | crontab -

echo "Entrées crontab CryptoLascar installées avec succès."
echo ""
echo "Crontab actuel :"
crontab -l

echo ""
echo "RAPPEL : Vérifier que le fuseau horaire du VPS est Europe/Paris :"
echo "  timedatectl | grep 'Time zone'"
echo "  Pour le modifier : sudo timedatectl set-timezone Europe/Paris"
