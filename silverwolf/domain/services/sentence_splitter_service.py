"""Domain Service: SentenceSplitterService.

Pure domain service for streaming token clause splitting per punctuation.
Implements low-latency boundary detection, safeguards for decimals, abbreviations,
emoticons, and roleplay asterisks, and extracts initial/inline emotion tags.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Generator, Iterable, Optional


# Indonesian and general abbreviations that end with a dot but do NOT terminate a sentence
ABBREVIATIONS = frozenset({
    "dll",
    "dsb",
    "dst",
    "dr",
    "prof",
    "s.d",
    "dkk",
    "tn",
    "ny",
    "hal",
    "no",
    "vol",
    "jl",
    "jln",
    "mr",
    "mrs",
    "ms",
    "etc",
    "vs",
    "tsb",
    "yth",
    "ttd",
})

COMPOUND_ABBREVIATIONS = frozenset({
    "s.d",
    "d.a",
    "u.p",
    "u.b",
    "a.n",
    "e.g",
    "i.e",
    "a.m",
    "p.m",
})

# Punctuation characters that may mark a clause or sentence boundary
STRONG_PUNCTUATION = frozenset({".", "!", "?", "…", "\n", "。", "！", "？"})
ALL_PUNCTUATION = STRONG_PUNCTUATION | frozenset({","})
CLOSING_QUOTES = frozenset({'"', "'", "”", "’", ")", "]", "}", "»"})


@dataclass(frozen=True)
class SplitterResult:
    """Represents a split sentence and its associated emotion."""
    emotion: Optional[str]
    text: str


class SentenceSplitterService:
    """Domain service to split streaming tokens or static text into clauses/sentences."""

    def __init__(
        self,
        min_sentence_length: int = 2,
        min_clause_length: int = 15,
    ):
        self.min_sentence_length = min_sentence_length
        self.min_clause_length = min_clause_length

    def split_stream(
        self,
        token_stream: Iterable[str],
    ) -> Generator[tuple[Optional[str], str], None, None]:
        """Consumes incoming token chunks and yields (detected_emotion, sentence_text)

        as each clause/sentence boundary is reached.
        """
        buffer = ""
        current_emotion: Optional[str] = None

        for token in token_stream:
            buffer += token

            # Extract leading emotion tag if present at start of buffer
            buffer, new_emotion = self._extract_leading_emotion(buffer)
            if new_emotion:
                current_emotion = new_emotion

            # Process completed clauses from the buffer
            while True:
                split_idx = self._find_split_point(buffer)
                if split_idx is None:
                    break

                clause = buffer[:split_idx].strip()
                buffer = buffer[split_idx:].lstrip()

                if clause:
                    # Check if clause had an inline emotion tag at its start
                    cleaned_clause, clause_emotion = self._extract_leading_emotion(clause)
                    if clause_emotion:
                        current_emotion = clause_emotion
                    if cleaned_clause:
                        yield (current_emotion, cleaned_clause)

                # Check if remainder now starts with a new emotion tag
                buffer, rem_emotion = self._extract_leading_emotion(buffer)
                if rem_emotion:
                    current_emotion = rem_emotion

        # Flush any remaining text at end-of-stream
        buffer, end_emotion = self._extract_leading_emotion(buffer)
        if end_emotion:
            current_emotion = end_emotion

        remaining = buffer.strip()
        if remaining:
            yield (current_emotion, remaining)

    def split_text(self, text: str) -> list[str]:
        """Convenience method for batch text sentence splitting."""
        if not text or not text.strip():
            return []
        return [sentence for _, sentence in self.split_stream([text])]

    def _extract_leading_emotion(self, text: str) -> tuple[str, Optional[str]]:
        """Extract [emotion] tag from beginning of text if present.

        Returns (cleaned_text, emotion_name).
        """
        stripped = text.lstrip()
        if not stripped.startswith("["):
            return text, None

        match = re.match(r"^\[([a-zA-Z0-9_\u4e00-\u9fa5]+)\]\s*", stripped)
        if match:
            emotion = match.group(1).lower()
            # Calculate how much to slice from the original text
            leading_whitespace_len = len(text) - len(stripped)
            tag_len = match.end()
            cleaned = text[leading_whitespace_len + tag_len:]
            return cleaned, emotion

        return text, None

    def _find_split_point(self, text: str) -> Optional[int]:
        """Scan text to find the earliest valid clause/sentence split point index.

        Returns the end index (exclusive) for the candidate clause, or None.
        """
        if not text:
            return None

        n = len(text)
        max_span = 50

        # State tracking for asterisks and brackets
        asterisk_start: Optional[int] = None
        bracket_stack: list[tuple[str, int]] = []
        bracket_pairs = {"(": ")", "[": "]", "{": "}"}

        i = 0
        while i < n:
            ch = text[i]

            # Newline reset: roleplay and brackets never span across newlines
            if ch == "\n":
                asterisk_start = None
                bracket_stack.clear()

            # Track roleplay asterisks (*...*)
            if ch == "*":
                if asterisk_start is None:
                    asterisk_start = i
                else:
                    asterisk_start = None
                i += 1
                continue

            # Track brackets and parentheses
            if ch in "({[":
                bracket_stack.append((ch, i))
                i += 1
                continue
            elif ch in ")}]":
                if bracket_stack:
                    bracket_stack.pop()
                i += 1
                continue

            # Check bounded state for asterisks
            if asterisk_start is not None:
                span = i - asterisk_start
                if span > max_span:
                    asterisk_start = None
                elif ch in STRONG_PUNCTUATION:
                    next_star = text.find("*", i + 1)
                    if next_star == -1 or (next_star - asterisk_start) > max_span:
                        asterisk_start = None

            # Check bounded state for brackets
            if bracket_stack:
                open_ch, open_idx = bracket_stack[-1]
                expected_closer = bracket_pairs.get(open_ch)
                span = i - open_idx
                if span > max_span:
                    bracket_stack.clear()
                elif ch in STRONG_PUNCTUATION:
                    closing_pos = text.find(expected_closer, i + 1) if expected_closer else -1
                    if closing_pos == -1 or (closing_pos - open_idx) > max_span:
                        bracket_stack.clear()

            # If still inside unclosed asterisks or brackets, do not split
            if asterisk_start is not None or len(bracket_stack) > 0:
                i += 1
                continue

            # Check for punctuation delimiter
            if ch in ALL_PUNCTUATION:
                # Comma rule: buffer before comma must have length >= min_clause_length
                if ch == ",":
                    # Decimal comma / thousands separator protection (e.g. "Rp 50.000,00", "3,14", "1,000")
                    if i > 0 and text[i - 1].isdigit():
                        if i + 1 < n:
                            if text[i + 1].isdigit():
                                i += 1
                                continue
                        else:
                            # Comma at buffer end preceded by digit: wait for potential digits
                            i += 1
                            continue

                    candidate_clause = text[: i + 1].strip()
                    if len(candidate_clause) < self.min_clause_length:
                        i += 1
                        continue

                # Period rules: safeguards for decimals, ellipses, abbreviations, lists
                if ch == ".":
                    if not self._is_valid_sentence_period(text, i):
                        i += 1
                        continue

                # Strong punctuation length check
                if ch in STRONG_PUNCTUATION:
                    candidate_clause = text[: i + 1].strip()
                    if len(candidate_clause) < self.min_sentence_length:
                        i += 1
                        continue

                # Valid split boundary found!
                # Include any consecutive punctuation marks (e.g. ?!, !!, ...) or closing quotes
                end_idx = i + 1
                while end_idx < n and (text[end_idx] in STRONG_PUNCTUATION or text[end_idx] in CLOSING_QUOTES):
                    end_idx += 1

                return end_idx

            i += 1

        return None

    def _is_valid_sentence_period(self, text: str, idx: int) -> bool:
        """Verify whether a period at idx is a true sentence boundary or a protected token."""
        n = len(text)

        # 1. Decimal numbers protection: digit before and digit after (e.g. 3.14)
        if idx > 0 and text[idx - 1].isdigit():
            if idx + 1 < n:
                if text[idx + 1].isdigit():
                    return False
            else:
                # At the very end of stream buffer, wait for potential upcoming digits
                return False

        # 2. Ellipsis protection: multiple consecutive dots like "..." or ".."
        if (idx + 1 < n and text[idx + 1] == ".") or (idx > 0 and text[idx - 1] == "."):
            # If not yet at the end of consecutive dots, do not split
            if idx + 1 < n and text[idx + 1] == ".":
                return False

        # 3. Numbered list protection: e.g. "^1." or " 2."
        prefix = text[:idx]
        if re.search(r"(?:^|\s)\d+$", prefix):
            # E.g. "1." - do not split on list number dot
            return False

        # 4. Indonesian and general abbreviation check: e.g. "dll.", "dsb.", "dr."
        preceding_word_match = re.search(r"([a-zA-Z]+)$", prefix)
        if preceding_word_match:
            word = preceding_word_match.group(1).lower()
            if word in ABBREVIATIONS:
                return False

        # 5. Compound abbreviation check: e.g. "s.d.", "e.g.", "i.e."
        # Case 5A: idx is at the second (or subsequent) dot, e.g. prefix ends with "s.d" or "e.g"
        compound_preceding = re.search(r"(?:^|\s|[0-9])([a-zA-Z](?:\.[a-zA-Z])+?)$", prefix, re.IGNORECASE)
        if compound_preceding:
            compound_word = compound_preceding.group(1).lower()
            if compound_word in COMPOUND_ABBREVIATIONS or compound_word in ABBREVIATIONS or re.fullmatch(r"[a-zA-Z]\.[a-zA-Z]", compound_word):
                return False

        # Case 5B: idx is at the first dot, e.g. prefix ends with single letter "s" and lookahead is ".d."
        single_letter_preceding = re.search(r"(?:^|\s|[0-9])([a-zA-Z])$", prefix)
        if single_letter_preceding:
            letter1 = single_letter_preceding.group(1).lower()
            lookahead_compound = re.match(r"^\.([a-zA-Z])\.", text[idx:], re.IGNORECASE)
            if lookahead_compound:
                return False
            elif idx + 1 >= n or (idx + 2 == n and text[idx + 1].isalpha()):
                # End of stream buffer: e.g. "... s." waiting for upcoming tokens
                return False

        # 6. Emoticon protection, e.g. T.T or ^.^ or ._.
        if idx > 0 and idx + 1 < n:
            prev_ch = text[idx - 1]
            next_ch = text[idx + 1]
            if prev_ch in "T^_-" and next_ch in "T^_-":
                return False

        return True
