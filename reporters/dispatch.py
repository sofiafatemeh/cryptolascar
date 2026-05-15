"""
reporters/dispatch.py — Sélection de rapports selon la date du jour (REPT-04).

Logique calendaire :
  - dernier jour du mois ET dimanche  → Monthly Close + Weekly Wrap (DEUX documents)
  - dernier jour du mois (semaine)    → Monthly Close
  - dimanche (sauf dernier du mois)   → Weekly Wrap
  - jours en semaine                  → Daily Report

Le dispatcher est le point d'intégration calendaire — Phase 5 (scheduler) appellera
`select_reports(datetime.date.today(), data, config)` à 07h00 / 08h00 CET.

Threat model :
  T-03-11 : La logique calendaire utilise `date.today()` au moment de l'appel.
             Phase 5 (scheduler) doit garantir le fuseau horaire CET pour que
             le Monthly Close soit déclenché le bon jour.
  T-03-12 : `_safe_build()` capture toute exception d'un builder — le run continue.
  T-03-13 : Les logs n'exposent jamais la config complète (clé API).
  T-03-14 : Clés explicites ("monthly", "weekly") — Phase 4 (delivery) distingue
             les deux emails à envoyer sans ambiguïté.
"""
from __future__ import annotations

import calendar
import datetime as _dt
from typing import Dict

from config import Config
from reporters.base import ReportOutput
from reporters.daily import build_daily_report
from reporters.weekly import build_weekly_report
from reporters.monthly import build_monthly_report
from logging_setup import get_logger

logger = get_logger(__name__)


def is_last_day_of_month(today: _dt.date) -> bool:
    """
    Retourne True si today est le dernier jour calendaire de son mois.

    Args:
        today: date à tester

    Returns:
        True si today.day == dernier jour du mois (via calendar.monthrange)
    """
    last = calendar.monthrange(today.year, today.month)[1]
    return today.day == last


def is_sunday(today: _dt.date) -> bool:
    """
    Retourne True si today est un dimanche.

    Args:
        today: date à tester

    Returns:
        True si today.weekday() == 6 (dimanche en Python)
    """
    return today.weekday() == 6


def _safe_build(builder, name: str, data: dict, config: Config) -> ReportOutput:
    """
    Wrapper qui ne lève jamais — encapsule l'échec d'un builder (T-03-12).

    Args:
        builder: callable (data, config) -> ReportOutput
        name: nom du rapport (pour le log)
        data: dict de données
        config: Config

    Returns:
        Le rapport construit, ou un ReportOutput dégradé si le builder lève.
    """
    try:
        return builder(data, config)
    except Exception as e:
        # T-03-13 : on logue uniquement le nom du rapport et le message, JAMAIS la config
        logger.error("%s build failed: %s", name, e)
        fallback_text = f"[{name} indisponible — erreur lors de la construction du rapport.]"
        fallback_html = (
            f'<p style="color:#e0e0e0;font-family:\'Courier New\',monospace;'
            f'font-size:14px;line-height:1.6;">{fallback_text}</p>'
        )
        return ReportOutput(html_body=fallback_html, plain_text=fallback_text)


def select_reports(today: _dt.date, data: dict, config: Config) -> Dict[str, ReportOutput]:
    """
    Retourne un dict des rapports à émettre pour la date `today`.

    Logique REPT-04 :
      - last_day AND sunday  → {"monthly": ..., "weekly": ...}  (deux documents)
      - last_day only        → {"monthly": ...}
      - sunday only          → {"weekly": ...}
      - else (weekday)       → {"daily": ...}

    Args:
        today: date du jour (date.today() en production)
        data: dict produit par collect_all()
        config: Config

    Returns:
        dict avec une ou plusieurs clés parmi {"daily", "weekly", "monthly"}.
        REPT-04 : si today est le dernier jour du mois ET un dimanche, le dict
        contient à la fois "monthly" et "weekly" (deux emails distincts).

    Ne lève jamais (T-03-12 — _safe_build absorbe les exceptions des builders).
    """
    last = is_last_day_of_month(today)
    sunday = is_sunday(today)
    result: Dict[str, ReportOutput] = {}

    if last and sunday:
        # REPT-04 — les DEUX rapports sont produits dans le même run
        # T-03-14 : clés explicites pour que Phase 4 (delivery) distingue les deux emails
        result["monthly"] = _safe_build(build_monthly_report, "Monthly Close", data, config)
        result["weekly"] = _safe_build(build_weekly_report, "Weekly Wrap", data, config)
    elif last:
        result["monthly"] = _safe_build(build_monthly_report, "Monthly Close", data, config)
    elif sunday:
        result["weekly"] = _safe_build(build_weekly_report, "Weekly Wrap", data, config)
    else:
        result["daily"] = _safe_build(build_daily_report, "Daily Report", data, config)

    return result
