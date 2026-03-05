#!/usr/bin/env python3
"""Normalize natural-language contract requirements into structured hints JSON."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROLE_HINTS = {
    "applicant": "Applicant",
    "agency": "Agency",
    "buyer": "Buyer",
    "seller": "Seller",
    "borrower": "Borrower",
    "lender": "Lender",
    "申請人": "Applicant",
    "機關": "Agency",
    "政府": "Agency",
    "買方": "Buyer",
    "賣方": "Seller",
    "借款人": "Borrower",
    "出借人": "Lender"
}

DATE_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}):(\d{2}))?(?:\s*UTC)?")
TOKEN_RE = re.compile(r"\b[A-Z]{2,10}\b")
AMOUNT_RE = re.compile(r"\b\d[\d,]*\b")
IGNORE_TOKENS = {"UTC", "JSON", "MOVE", "EN", "ZH", "DEX"}
NAME_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")
IGNORE_NAMES = {
    "Requirement",
    "Timeout",
    "Approve",
    "Reject",
    "Swap",
    "Close",
    "UTC",
}


@dataclass
class MissingField:
    field: str
    reason: str


@dataclass
class Ambiguity:
    field: str
    reason: str


@dataclass
class ClarificationQuestion:
    id: str
    question: str
    reason: str


def detect_language(text: str) -> str:
    has_cjk = any("\u4e00" <= ch <= "\u9fff" for ch in text)
    has_ascii = any("a" <= ch.lower() <= "z" for ch in text)
    if has_cjk and has_ascii:
        return "mixed"
    if has_cjk:
        return "zh"
    if has_ascii:
        return "en"
    return "unknown"


def parse_deadlines(text: str) -> list[dict]:
    deadlines = []
    for i, match in enumerate(DATE_RE.finditer(text), start=1):
        y, m, d, hh, mm, ss = match.groups()
        h = int(hh) if hh is not None else 23
        mi = int(mm) if mm is not None else 59
        s = int(ss) if ss is not None else 59
        dt = datetime(int(y), int(m), int(d), h, mi, s, tzinfo=timezone.utc)
        deadlines.append({
            "label": f"deadline_{i}",
            "raw": match.group(0),
            "unix": int(dt.timestamp())
        })
    return deadlines


def parse_parties(text: str) -> list[str]:
    parties: list[str] = []
    lowered = text.lower()
    for hint, role in ROLE_HINTS.items():
        if hint in lowered or hint in text:
            if role not in parties:
                parties.append(role)
    if len(parties) < 2:
        for name in detect_named_party_candidates(text):
            if name not in parties:
                parties.append(name)
    return parties


def parse_tokens(text: str) -> list[dict]:
    seen = set()
    tokens = []
    for token in TOKEN_RE.findall(text):
        if token in IGNORE_TOKENS:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append({"currency_symbol": "", "token_name": token})
    return tokens


def parse_money_mentions(text: str) -> list[dict]:
    date_spans = [m.span() for m in DATE_RE.finditer(text)]

    def in_date_span(idx: int) -> bool:
        for start, end in date_spans:
            if start <= idx < end:
                return True
        return False

    amounts = []
    i = 0
    for match in AMOUNT_RE.finditer(text):
        if in_date_span(match.start()):
            continue
        raw = match.group(0)
        # Ignore list numbering like "1)" / "2)" to reduce noise.
        if len(raw) == 1 and match.end() < len(text) and text[match.end()] == ")":
            continue
        cleaned = int(raw.replace(",", ""))
        i += 1
        amounts.append({
            "label": f"amount_{i}",
            "raw_amount": raw,
            "minor_units": cleaned
        })
    return amounts


def detect_named_party_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for name in NAME_RE.findall(text):
        if name.upper() == name:
            continue
        if name in IGNORE_NAMES:
            continue
        if name not in candidates:
            candidates.append(name)
    return candidates


def build_missing(parties: list[str], tokens: list[dict], deadlines: list[dict], amounts: list[dict]) -> list[MissingField]:
    missing: List[MissingField] = []
    if len(parties) < 2:
        missing.append(MissingField("parties", "At least two role parties are recommended for multi-party contracts."))
    if not tokens:
        missing.append(MissingField("token.token_name", "Token must be explicit in supported subset."))
    if not deadlines:
        missing.append(MissingField("timeout", "Marlowe requires explicit absolute timeout values."))
    if not amounts:
        missing.append(MissingField("money", "At least one monetary amount is required."))
    return missing


def build_ambiguities(
    raw_text: str,
    parties: list[str],
    tokens: list[dict],
    deadlines: list[dict],
    amounts: list[dict],
) -> list[Ambiguity]:
    ambiguities: List[Ambiguity] = []

    names = detect_named_party_candidates(raw_text)
    if not parties and len(names) >= 2:
        ambiguities.append(
            Ambiguity(
                "parties.mapping",
                f"Detected possible participants {names[:4]}; confirm how to map into role_token parties.",
            )
        )

    if len(tokens) > 1:
        token_names = [t["token_name"] for t in tokens if isinstance(t.get("token_name"), str)]
        ambiguities.append(
            Ambiguity(
                "token.mapping",
                f"Detected multiple tokens {token_names}; confirm maker/taker token mapping.",
            )
        )

    if len(deadlines) >= 2:
        ambiguities.append(
            Ambiguity(
                "timeout.mapping",
                "Multiple deadlines found; confirm which deadline maps to each contract stage.",
            )
        )

    if len(amounts) >= 3:
        ambiguities.append(
            Ambiguity(
                "money.mapping",
                "Multiple amounts found; confirm amount-to-action mapping (deposit/pay/refund).",
            )
        )

    return ambiguities


def build_questions(missing: list[MissingField], ambiguities: list[Ambiguity]) -> list[ClarificationQuestion]:
    questions: list[ClarificationQuestion] = []
    seen_ids: set[str] = set()

    def add(qid: str, question: str, reason: str) -> None:
        if qid in seen_ids or len(questions) >= 3:
            return
        seen_ids.add(qid)
        questions.append(ClarificationQuestion(qid, question, reason))

    for item in missing:
        if item.field.startswith("parties"):
            add(
                "party_roles",
                "請提供至少兩個 role_token 角色名稱（例如 Buyer / Seller）。",
                item.reason,
            )
        elif item.field.startswith("token"):
            add(
                "token_required",
                "請至少指定一種 token（可指定兩種做 swap）。",
                item.reason,
            )
        elif item.field == "timeout":
            add(
                "absolute_timeouts",
                "請提供每個階段的絕對 UTC 時間（YYYY-MM-DD HH:MM:SS UTC）。",
                item.reason,
            )
        elif item.field == "money":
            add(
                "money_amounts",
                "請提供整數最小單位金額，並說明每筆金額對應的動作。",
                item.reason,
            )

    for item in ambiguities:
        if item.field == "timeout.mapping":
            add(
                "timeout_mapping",
                "請確認每個 deadline 對應哪個步驟（例如 deposit deadline、review deadline）。",
                item.reason,
            )
        elif item.field == "parties.mapping":
            add(
                "party_mapping",
                "請確認參與者如何映射到 role_token（例如 Alice->Buyer, Bob->Seller）。",
                item.reason,
            )
        elif item.field == "money.mapping":
            add(
                "amount_mapping",
                "請確認每個 amount 對應 deposit/pay/refund 哪一個動作。",
                item.reason,
            )
        elif item.field == "token.mapping":
            add(
                "token_mapping",
                "請確認多 token 的角色映射（例如 maker_token=SUI, taker_token=USDC）。",
                item.reason,
            )

    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize requirement text into domain hints JSON")
    parser.add_argument("input", help="Path to UTF-8 text/markdown requirement file")
    args = parser.parse_args()

    raw_text = Path(args.input).read_text(encoding="utf-8")
    parties = parse_parties(raw_text)
    tokens = parse_tokens(raw_text)
    deadlines = parse_deadlines(raw_text)
    amounts = parse_money_mentions(raw_text)
    missing_items = build_missing(parties, tokens, deadlines, amounts)
    ambiguity_items = build_ambiguities(raw_text, parties, tokens, deadlines, amounts)
    question_items = build_questions(missing_items, ambiguity_items)
    missing = [asdict(item) for item in missing_items]
    ambiguities = [asdict(item) for item in ambiguity_items]
    questions = [asdict(item) for item in question_items]

    payload = {
        "raw_text": raw_text,
        "language": detect_language(raw_text),
        "parties": parties,
        "tokens": tokens,
        "deadlines": deadlines,
        "money_mentions": amounts,
        "missing": missing,
        "ambiguities": ambiguities,
        "questions": questions
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
