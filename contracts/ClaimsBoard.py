# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re
import hashlib
from datetime import datetime, timezone
from genlayer import *

MAX_HEADLINE_CHARS = 140
MIN_HEADLINE_CHARS = 5


def _parse_iso8601_utc(dt_str: str) -> tuple[int, str]:
    if not isinstance(dt_str, str):
        raise gl.vm.UserError("datetime must be string")
    clean_dt = dt_str.strip()
    if not clean_dt:
        raise gl.vm.UserError("empty datetime")

    try:
        iso_clean = clean_dt[:-1] + "+00:00" if clean_dt.endswith("Z") else clean_dt
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        ts_int = int(dt.timestamp())
        utc_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return (ts_int, utc_iso)
    except Exception:
        raise gl.vm.UserError("invalid ISO-8601 datetime format")


def _get_current_timestamp() -> tuple[int, str]:
    if hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
        raw_dt = gl.message_raw.get("datetime")
        if raw_dt:
            return _parse_iso8601_utc(str(raw_dt))
    raise gl.vm.UserError("clock unavailable")


def _derive_badge_from_status(status_str: str) -> str:
    """
    Map ledger status string 'STATUS|CLASS|AUDITS_TOTAL|LATEST_AUDITED_AT' to badge:
    - UNAUDITED -> UNAUDITED
    - HEALTHY + UNCHANGED -> VERIFIED
    - HEALTHY + COSMETIC -> REPHRASED
    - DRIFTED -> DRIFTED
    - REMOVED -> REMOVED
    """
    parts = str(status_str).split("|")
    status = parts[0] if len(parts) > 0 else "UNAUDITED"
    latest_class = parts[1] if len(parts) > 1 else "NONE"

    if status == "UNAUDITED":
        return "UNAUDITED"
    if status == "HEALTHY":
        if latest_class == "COSMETIC":
            return "REPHRASED"
        return "VERIFIED"
    if status == "DRIFTED":
        return "DRIFTED"
    if status == "REMOVED":
        return "REMOVED"
    return "UNAUDITED"


class ClaimsBoard(gl.Contract):
    owner: str
    ledger_address: str
    claims: TreeMap[str, str]
    claim_ids: TreeMap[str, str]
    meta: TreeMap[str, str]

    def __init__(self):
        self.owner = gl.message.sender_address.as_hex
        self.ledger_address = ""

    def _ensure_meta_init(self) -> None:
        if "nonce" not in self.meta:
            self.meta["nonce"] = "0"
        if "claims_total" not in self.meta:
            self.meta["claims_total"] = "0"

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner

    @gl.public.view
    def get_ledger_address(self) -> str:
        return self.ledger_address

    @gl.public.view
    def get_claim(self, entry_id: str) -> str:
        eid = str(entry_id).strip()
        if eid not in self.claims:
            raise gl.vm.UserError("claim not found")
        return self.claims[eid]

    @gl.public.view
    def list_claim_ids(self, offset: int, limit: int) -> str:
        total = int(self.meta.get("claims_total", "0"))
        all_ids = [self.claim_ids[str(i)] for i in range(total)]
        off = max(0, int(offset))
        lim = max(0, int(limit))
        reversed_ids = list(reversed(all_ids))
        sliced = reversed_ids[off:off + lim] if lim > 0 else reversed_ids[off:]
        return json.dumps(sliced)

    @gl.public.write
    def set_ledger(self, ledger_address: str) -> None:
        """One-time configuration of the SourceDriftLedger contract address by the owner."""
        sender = gl.message.sender_address.as_hex
        if sender.lower() != self.owner.lower():
            raise gl.vm.UserError("only owner can set ledger address")

        if self.ledger_address != "":
            raise gl.vm.UserError("ledger address already set")

        clean_addr = str(ledger_address).strip()
        if not clean_addr.startswith("0x") or len(clean_addr) != 42:
            raise gl.vm.UserError("invalid ledger contract address format")

        try:
            int(clean_addr[2:], 16)
        except ValueError:
            raise gl.vm.UserError("invalid hex address")

        self.ledger_address = clean_addr

    @gl.public.write
    def publish_claim(self, citation_id: str, headline: str) -> None:
        """
        Publish a claim bound to an existing SourceDriftLedger citation.
        Queries the ledger via cross-contract view call to initialize its verified status badge.
        """
        if not self.ledger_address:
            raise gl.vm.UserError("ledger not set")

        if not isinstance(headline, str):
            raise gl.vm.UserError("headline must be string")
        clean_headline = " ".join(headline.split())
        if len(clean_headline) < MIN_HEADLINE_CHARS or len(clean_headline) > MAX_HEADLINE_CHARS:
            raise gl.vm.UserError(f"headline length must be between {MIN_HEADLINE_CHARS} and {MAX_HEADLINE_CHARS} characters")

        cid = str(citation_id).strip()
        if not cid:
            raise gl.vm.UserError("citation_id cannot be empty")

        ledger = gl.get_contract_at(Address(self.ledger_address))
        status_str = ledger.view().get_status(cid)

        badge = _derive_badge_from_status(status_str)
        sender = gl.message.sender_address.as_hex
        current_ts, now_str = _get_current_timestamp()

        self._ensure_meta_init()
        current_nonce = int(self.meta.get("nonce", "0")) + 1
        self.meta["nonce"] = str(current_nonce)
        total_claims = int(self.meta.get("claims_total", "0"))

        entry_preimage = f"{sender}|{cid}|{clean_headline}|{current_nonce}".encode("utf-8")
        entry_id = hashlib.sha256(entry_preimage).hexdigest()[:12]

        entry = {
            "id": entry_id,
            "headline": clean_headline,
            "citation_id": cid,
            "publisher": sender,
            "published_at": now_str,
            "published_at_ts": current_ts,
            "badge": badge,
            "badge_history": [badge],
        }

        self.claims[entry_id] = json.dumps(entry)
        self.claim_ids[str(total_claims)] = entry_id
        self.meta["claims_total"] = str(total_claims + 1)

    @gl.public.write
    def refresh_claim(self, entry_id: str) -> None:
        """
        Re-reads citation status from SourceDriftLedger and updates claim badge.
        Appends to badge_history ONLY when the badge changes (no duplicate entries).
        """
        if not self.ledger_address:
            raise gl.vm.UserError("ledger not set")

        eid = str(entry_id).strip()
        if eid not in self.claims:
            raise gl.vm.UserError("claim not found")

        claim = json.loads(self.claims[eid])
        cid = claim["citation_id"]

        ledger = gl.get_contract_at(Address(self.ledger_address))
        status_str = ledger.view().get_status(cid)

        new_badge = _derive_badge_from_status(status_str)
        old_badge = claim.get("badge")

        if new_badge != old_badge:
            claim["badge"] = new_badge
            history = claim.get("badge_history", [])
            history.append(new_badge)
            claim["badge_history"] = history
            self.claims[eid] = json.dumps(claim)
