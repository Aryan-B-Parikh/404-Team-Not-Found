"""Agent provider resolution — pure logic, no network, no DB."""

from __future__ import annotations

from app.services.llm import _resolve


def test_auto_prefers_bob_then_deterministic():
    assert _resolve("auto", True) == "bob"
    assert _resolve("auto", False) == "deterministic"


def test_explicit_provider_wins():
    assert _resolve("deterministic", True) == "deterministic"
    assert _resolve("bob", False) == "bob"
