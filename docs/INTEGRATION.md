# CitationWatch Frontend dApp Integration Guide

This guide specifies all public methods, parameter formats, JSON return shapes, and revert messages for frontend and client developers integrating with **SourceDriftLedger** and **ClaimsBoard**.

## Network Details
- **Network**: GenLayer Studionet (Preview)
- **Chain ID**: `61999`
- **RPC Endpoint**: `https://studio.genlayer.com/api`
- **Explorer**: `https://explorer-studio.genlayer.com`
- **SourceDriftLedger Address**: `0xFC7593432D4e8A2ceda911497807E4aCC7c7B705`
- **ClaimsBoard Address**: `0x057fA33Ed3508AAe0051d72e81dD6B0Ba52009aD`

---

## 1. SourceDriftLedger API Reference

### Write Methods

#### `register_citation(label: str, baseline_url: str, quotes_json: str) -> None`
Registers a new citation against an immutable Wikipedia revision baseline.
- **Parameters**:
  - `label`: Descriptive string (1 to 120 characters).
  - `baseline_url`: Canonical Wikipedia revision permalink: `https://<lang>.wikipedia.org/w/index.php?title=<Title>&oldid=<OldId>`.
  - `quotes_json`: JSON-encoded string containing a list of 1 to 4 verbatim quotes. Each quote must be 30 to 240 characters and present verbatim in the baseline text.
- **Example Payload**:
  ```json
  [
    "In the 1940s, Turing became worried about losing his savings in the event of a German invasion."
  ]
  ```
- **Revert Conditions**:
  - `"label exceeds maximum length of 120 characters"`
  - `"baseline must be an immutable revision permalink"`
  - `"quotes must be a list of 1 to 4 items"`
  - `"quote 1 length must be between 30 and 240 characters"`
  - `"quote not found verbatim in baseline"`
  - `"duplicate quote"`
  - `"already registered"`
  - `"source unavailable"`

#### `audit_citation(citation_id: str, target_url: str) -> None`
Audits an existing citation against a target revision or the live Wikipedia page.
- **Parameters**:
  - `citation_id`: 12-character hex ID returned from registration.
  - `target_url`:
    - Later revision permalink: `https://<lang>.wikipedia.org/w/index.php?title=<Title>&oldid=<NewOldId>` where `int(NewOldId) > int(BaselineOldId)`.
    - Live page: `https://<lang>.wikipedia.org/wiki/<Title>`.
- **Revert Conditions**:
  - `"citation not found"`
  - `"target title must match baseline title"`
  - `"target URL host must match baseline host"`
  - `"target revision must be later than baseline"`
  - `"target already audited"` (for REVISION targets)
  - `"live audit cooldown active"` (300-second cooldown for LIVE targets)
  - `"source unavailable"`
  - `"coverage insufficient to conclude absence"`

### View Methods

#### `get_status(citation_id: str) -> str`
Returns a compact pipelined string designed for low-overhead consumer calls:
```
"{STATUS}|{CLASS}|{AUDITS_TOTAL}|{LATEST_AUDITED_AT}"
```
- **Statuses**: `UNAUDITED`, `HEALTHY`, `DRIFTED`, `REMOVED`.
- **Classes**: `NONE`, `UNCHANGED`, `COSMETIC`, `MATERIAL`, `REMOVED`.
- **Example**: `"HEALTHY|UNCHANGED|1|2026-10-16T12:00:00Z"`.

#### `get_citation(citation_id: str) -> str`
Returns the complete JSON citation object:
```json
{
  "schema_version": "1.0.0",
  "citation_id": "a984e9a3885e",
  "label": "Alan Turing Silver Savings",
  "registrant": "0x...",
  "registered_at": "2026-10-16T12:00:00Z",
  "registered_at_ts": 1792152000,
  "baseline_url": "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434",
  "baseline_host": "en.wikipedia.org",
  "baseline_title": "Alan Turing",
  "baseline_oldid": "1379625434",
  "elements": [
    {
      "id": "e1",
      "quote": "In the 1940s, Turing became worried about losing his savings in the event of a German invasion.",
      "quote_sha256": "..."
    }
  ],
  "baseline_text_sha256": "...",
  "baseline_chars_total": 119843,
  "fetch_method": "web.render",
  "latest_audit_index": 0,
  "status": "HEALTHY",
  "audits_total": 1,
  "audits": [
    {
      "n": 1,
      "auditor": "0x...",
      "audited_at": "2026-10-16T12:05:00Z",
      "audited_at_ts": 1792152300,
      "target_url": "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
      "target_kind": "REVISION",
      "target_oldid": "1380390650",
      "class": "UNCHANGED",
      "elements": [
        {
          "id": "e1",
          "status": "SAME",
          "decided_by": "DETERMINISTIC",
          "passage_id": null,
          "cited_quote": "In the 1940s, Turing became worried about losing his savings in the event of a German invasion."
        }
      ],
      "passages": [],
      "target_text_sha256": "...",
      "presented_segment_ids": [],
      "presented_segments_count": 0,
      "source_chars_total": 119843,
      "source_chars_inspected": 119843,
      "budget_chars_used": 119843,
      "truncated_at": false,
      "coverage": "FULL",
      "fetch_method": "web.render",
      "fingerprint_in_consensus": true
    }
  ]
}
```

#### `list_citation_ids(offset: int, limit: int) -> str`
Returns a JSON-encoded array of citation IDs, ordered newest-first:
`["a984e9a3885e", ...]`

---

## 2. ClaimsBoard API Reference

### Write Methods

#### `publish_claim(citation_id: str, headline: str) -> None`
Publishes a public headline backed by an on-chain citation. Queries `SourceDriftLedger.get_status(citation_id)` via cross-contract call to initialize the verified badge.
- **Parameters**:
  - `citation_id`: Valid citation ID on the connected ledger.
  - `headline`: Statement string between 5 and 140 characters.

#### `refresh_claim(entry_id: str) -> None`
Re-queries the citation status from the ledger and updates the claim badge. Appends to `badge_history` only if the badge changed.

### View Methods

#### `get_claim(entry_id: str) -> str`
Returns the claim JSON record:
```json
{
  "id": "175c4c8df043",
  "headline": "Turing silver savings confirmed on Wikipedia",
  "citation_id": "a984e9a3885e",
  "publisher": "0x...",
  "published_at": "2026-10-16T12:10:00Z",
  "published_at_ts": 1792152600,
  "badge": "VERIFIED",
  "badge_history": ["VERIFIED"]
}
```

#### `list_claim_ids(offset: int, limit: int) -> str`
Returns a JSON list of claim entry IDs, ordered newest-first.
