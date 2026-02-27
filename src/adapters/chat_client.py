"""Shared chat client interfaces for free-text Q&A."""

from __future__ import annotations

from typing import Protocol


class ChatAnswerClient(Protocol):
    def answer(self, user_text: str) -> str:
        """Return a non-executing chat answer for user free text."""

