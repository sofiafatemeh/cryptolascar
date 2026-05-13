"""
scheduler/utils.py — Utilitaires calendaires pour le scheduler CryptoLascar.

D-07: scheduler/jobs.py n'est pas créé — seules des fonctions utilitaires ici.
"""
from __future__ import annotations
import calendar
import datetime


def is_last_day_of_month(today: datetime.date) -> bool:
    """
    Retourne True si today est le dernier jour calendaire de son mois (D-03).

    Args:
        today: date à tester

    Returns:
        True si today.day == calendar.monthrange(today.year, today.month)[1]
    """
    last = calendar.monthrange(today.year, today.month)[1]
    return today.day == last
