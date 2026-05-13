"""
tests/test_scheduler_utils.py — Tests TDD pour scheduler/utils.py.

RED phase : ces tests échouent jusqu'à ce que is_last_day_of_month() soit implémenté.
"""
from __future__ import annotations

import datetime

import pytest


def test_last_day_january():
    """31 janvier est le dernier jour de janvier."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 1, 31)) is True


def test_not_last_day_january():
    """30 janvier n'est pas le dernier jour de janvier."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 1, 30)) is False


def test_last_day_february_non_leap():
    """28 février est le dernier jour de février (année non bissextile)."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 2, 28)) is True


def test_last_day_february_leap():
    """29 février est le dernier jour de février (année bissextile)."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2024, 2, 29)) is True


def test_last_day_december():
    """31 décembre est le dernier jour de décembre."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 12, 31)) is True


def test_first_day_not_last():
    """1er janvier n'est pas le dernier jour de janvier."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 1, 1)) is False


def test_last_day_april():
    """30 avril est le dernier jour d'avril (30 jours)."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 4, 30)) is True


def test_not_last_day_april():
    """29 avril n'est pas le dernier jour d'avril."""
    from scheduler.utils import is_last_day_of_month
    assert is_last_day_of_month(datetime.date(2026, 4, 29)) is False
