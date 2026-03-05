#!/usr/bin/env python3
"""Summarize a Marlowe JSON contract into concise metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def walk(node: Any, stats: dict) -> None:
    if isinstance(node, str):
        if node == "close":
            stats["contracts"]["close"] += 1
        return

    if not isinstance(node, dict):
        return

    if "pay" in node:
        stats["contracts"]["pay"] += 1
        party = node.get("from_account", {}).get("role_token")
        if party:
            stats["parties"].add(party)
        token = node.get("token", {}).get("token_name")
        if token:
            stats["tokens"].add(token)
        walk(node.get("then"), stats)
        return

    if "if" in node and "then" in node and "else" in node:
        stats["contracts"]["if"] += 1
        walk(node.get("then"), stats)
        walk(node.get("else"), stats)
        return

    if "when" in node:
        stats["contracts"]["when"] += 1
        stats["timeouts"].append(node.get("timeout"))
        for case in node.get("when", []):
            action = case.get("case", {})
            if "deposits" in action:
                stats["actions"]["deposit"] += 1
                party = action.get("party", {}).get("role_token")
                if party:
                    stats["parties"].add(party)
                token = action.get("of_token", {}).get("token_name")
                if token:
                    stats["tokens"].add(token)
            elif "for_choice" in action:
                stats["actions"]["choice"] += 1
                owner = action.get("for_choice", {}).get("choice_owner", {}).get("role_token")
                if owner:
                    stats["parties"].add(owner)
            elif "notify_if" in action:
                stats["actions"]["notify"] += 1
            walk(case.get("then"), stats)
        walk(node.get("timeout_continuation"), stats)
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Marlowe contract")
    parser.add_argument("contract", help="Path to contract JSON")
    args = parser.parse_args()

    root = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    if isinstance(root, dict) and "contract" in root and "status" in root:
        root = root["contract"]

    stats = {
        "contracts": {"close": 0, "pay": 0, "if": 0, "when": 0},
        "actions": {"deposit": 0, "choice": 0, "notify": 0},
        "parties": set(),
        "tokens": set(),
        "timeouts": []
    }

    walk(root, stats)

    payload = {
        "status": "ok",
        "summary": {
            "contracts": stats["contracts"],
            "actions": stats["actions"],
            "parties": sorted(stats["parties"]),
            "tokens": sorted(stats["tokens"]),
            "timeouts": [t for t in stats["timeouts"] if isinstance(t, int)]
        }
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
