# SPDX-License-Identifier: MIT
"""Payout tracker -- check pending transfers and history against a
RustChain node.
"""

from __future__ import annotations

from typing import List

import requests

from concierge import config


def check_pending(wallet_id: str, node_url: str | None = None) -> List[dict]:
    """Return pending transfers for *wallet_id*.

    Queries ``GET {node_url}/wallet/pending?miner_id={wallet_id}``.
    Returns an empty list on 404 or connection errors.
    """
    base = (node_url or config.RUSTCHAIN_NODE_URL).rstrip("/")
    url = f"{base}/wallet/pending"
    try:
        resp = requests.get(
            url,
            params={"miner_id": wallet_id},
            timeout=15,
            verify=False,  # self-signed cert on node
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("pending", [])
    except requests.RequestException:
        return []


def check_history(wallet_id: str, node_url: str | None = None) -> List[dict]:
    """Return recent transfer history for *wallet_id*.

    Queries ``GET {node_url}/wallet/history?miner_id={wallet_id}``.
    Returns an empty list on 404 or connection errors.
    """
    base = (node_url or config.RUSTCHAIN_NODE_URL).rstrip("/")
    url = f"{base}/wallet/history"
    try:
        resp = requests.get(
            url,
            params={"miner_id": wallet_id},
            timeout=15,
            verify=False,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("transactions") or data.get("history", [])
    except requests.RequestException:
        return []


def format_payout_status(pending: List[dict], history: List[dict]) -> str:
    """Pretty-print payout status for CLI output.

    Parameters
    ----------
    pending : list[dict]
        Items from :func:`check_pending`.  Each dict should have at least
        ``amount_rtc`` and optionally ``memo``, ``created_at``.
    history : list[dict]
        Items from :func:`check_history`.  Each dict should have at least
        ``amount_rtc`` (or ``amount``), ``from``, ``to`` (or direction inferred from ``type``),
        and optionally ``timestamp``.
    """
    lines: list[str] = []

    # Pending
    lines.append("-- Pending Transfers --")
    if not pending:
        lines.append("  (none)")
    else:
        for item in pending:
            amount = item.get("amount_rtc") if "amount_rtc" in item else item.get("amount", "?")
            memo = item.get("memo", "")
            ts = item.get("created_at") or item.get("timestamp", "")
            entry = f"  {amount} RTC"
            if memo:
                entry += f"  memo: {memo}"
            if ts:
                entry += f"  ({ts})"
            lines.append(entry)

    lines.append("")

    # History
    lines.append("-- Recent History --")
    if not history:
        lines.append("  (none)")
    else:
        for item in history:
            amount = item.get("amount_rtc") if "amount_rtc" in item else item.get("amount", "?")
            sender = item.get("from", "?")
            recipient = item.get("to")
            if recipient is None:
                tx_type = item.get("type", "")
                if tx_type == "transfer_in":
                    recipient = "(you)"
                else:
                    recipient = "?"
            ts = item.get("timestamp", "")
            entry = f"  {amount} RTC  {sender} -> {recipient}"
            if ts:
                entry += f"  ({ts})"
            lines.append(entry)

    return "\n".join(lines)
