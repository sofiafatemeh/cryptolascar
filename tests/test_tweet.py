"""tests/test_tweet.py — TDD RED: tests for delivery/tweet.py (write_tweet, extract_one_signal, HASHTAG_POOL)."""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from delivery.tweet import HASHTAG_POOL, extract_one_signal, write_tweet
from config import Config


def _make_config(**overrides) -> Config:
    defaults = dict(
        smtp_host="smtp.gmail.com",
        smtp_port=465,
        smtp_user="sender@gmail.com",
        smtp_password="secret",
        recipient_list=["alice@example.com"],
        anthropic_api_key="sk-test-key",
        anthropic_model="claude-sonnet-4-6",
        coingecko_api_key="",
        alpha_vantage_key="",
        fred_api_key="",
        newsapi_key="",
        db_path=Path("test.db"),
        log_level="INFO",
        log_file="",
    )
    defaults.update(overrides)
    return Config(**defaults)


DAILY_REPORT = (
    "## Macro Snapshot\n\nMacro body text.\n\n"
    "## ETF Radar\n\nETF body text.\n\n"
    "## One Signal\n\nAcheter IWDA.AS sur repli — momentum haussier confirmé.\n"
)

WEEKLY_REPORT = (
    "## Executive Summary\n\nBilan de la semaine positive.\n\n"
    "## Outlook\n\nSemaine prochaine prudence recommandée.\n"
)

TWEET_240 = "A" * 200 + " #Bourse #ETF #Crypto #Finance"  # ~230 chars — outside range for test 9
TWEET_OK = (
    "Momentum haussier sur les marchés européens cette semaine. "
    "Les ETFs PEA affichent +1.2% de progression notable, portés par la tech et l'immobilier. "
    "Surveillance renforcée sur la crypto en cette période volatile. "
    "#Bourse #ETF #CAC40 #Investissement"
)
assert 240 <= len(TWEET_OK) <= 270, f"TWEET_OK length {len(TWEET_OK)} is outside [240, 270]"


# --- HASHTAG_POOL ---

def test_hashtag_pool_is_valid():
    assert len(HASHTAG_POOL) >= 6
    assert all(h.startswith("#") for h in HASHTAG_POOL)


# --- extract_one_signal ---

def test_extract_one_signal_finds_section():
    text = "## Macro\n\nMacro body\n\n## One Signal\n\nSignal text here\n"
    assert extract_one_signal(text) == "Signal text here"


def test_extract_one_signal_returns_empty_when_missing():
    text = "## Macro\n\nMacro body\n"
    assert extract_one_signal(text) == ""


# --- write_tweet routing ---

def test_write_tweet_monthly_returns_none_no_file(tmp_path):
    # monthly skips before path construction — no _TWEETS_DIR patch needed
    cfg = _make_config()
    result = write_tweet("monthly", "2026-05-31", "full monthly report text", cfg)
    assert result is None
    assert not (tmp_path / "tweets" / "2026-05-31.txt").exists()


# --- write_tweet daily ---

def test_write_tweet_daily_calls_anthropic_with_correct_model(tmp_path):
    # Patch _TWEETS_DIR so write_tweet writes to tmp_path/tweets (WR-03 fix)
    cfg = _make_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=TWEET_OK)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    create_kwargs = mock_client.messages.create.call_args[1]
    assert create_kwargs.get("model") == cfg.anthropic_model


def test_write_tweet_daily_writes_file(tmp_path):
    cfg = _make_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=TWEET_OK)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    assert (tmp_path / "tweets" / "2026-05-10.txt").exists()


def test_write_tweet_weekly_writes_file(tmp_path):
    cfg = _make_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=TWEET_OK)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            write_tweet("weekly", "2026-05-10", WEEKLY_REPORT, cfg)
    assert (tmp_path / "tweets" / "2026-05-10.txt").exists()


def test_write_tweet_file_content_equals_claude_response(tmp_path):
    cfg = _make_config()
    expected = "Tweet content from Claude. #Bourse #ETF #Crypto #Finance"
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=expected)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    actual = (tmp_path / "tweets" / "2026-05-10.txt").read_text(encoding="utf-8")
    assert actual == expected


def test_write_tweet_logs_warning_for_short_tweet_but_writes_anyway(tmp_path, caplog):
    cfg = _make_config()
    short_tweet = "Court"  # 5 chars — well outside [240, 270]
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=short_tweet)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            with caplog.at_level(logging.WARNING):
                write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    assert (tmp_path / "tweets" / "2026-05-10.txt").exists()
    assert any("240" in r.message or "270" in r.message or "length" in r.message.lower() for r in caplog.records)


def test_write_tweet_never_logs_api_key_on_failure(tmp_path, caplog):
    cfg = _make_config(anthropic_api_key="sk-super-secret-key")
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", side_effect=Exception("api error")):
            with pytest.raises(Exception):
                with caplog.at_level(logging.ERROR):
                    write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    assert "sk-super-secret-key" not in caplog.text


def test_write_tweet_reraises_on_claude_failure(tmp_path):
    cfg = _make_config()
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", side_effect=Exception("connection error")):
            with pytest.raises(Exception):
                write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)


def test_write_tweet_prompt_contains_one_signal_text(tmp_path):
    cfg = _make_config()
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [MagicMock(type="text", text=TWEET_OK)]
    with patch("delivery.tweet._TWEETS_DIR", tmp_path / "tweets"):
        with patch("delivery.tweet.Anthropic", return_value=mock_client):
            write_tweet("daily", "2026-05-10", DAILY_REPORT, cfg)
    create_kwargs = mock_client.messages.create.call_args[1]
    prompt_sent = create_kwargs["messages"][0]["content"]
    # The extracted ONE SIGNAL text should appear in the prompt
    assert "momentum haussier" in prompt_sent.lower() or "one signal" in prompt_sent.lower()
