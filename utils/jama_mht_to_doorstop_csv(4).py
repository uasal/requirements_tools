#!/usr/bin/env python3
"""Parse a JAMA-exported Word/MHT file and convert requirement tables to CSV.

Each requirement in the MHT file is represented as an individual two-column
HTML table where:
  - Column 0 = field label  (e.g. "Name", "Legacy ID", "Description", …)
  - Column 1 = field value

The script:
  1. Decodes the base64-encoded HTML body from the MHT (MIME-HTML) envelope.
     JAMA typically encodes the HTML as UTF-16LE ("unicode" charset).
  2. Parses every <table> element and treats each row as a label/value pair.
  3. Groups the rows into one record per requirement table.
  4. Maps JAMA field names to doorstop CSV columns:
       "Legacy ID"            → uid
       "Name"                 → header
       "Description"          → text
       "Project ID"           → project_id
       "Global ID"            → global_id
       "Created"              → created
       "Modified" /
       "Last Modified" /
       "Date Modified"        → modified
  5. Extracts parent requirement links from "Additional Notes" text
     (pattern: "Parents:" followed by Legacy-ID tokens such as OBJ-13).
     Parent IDs are stored in the doorstop ``links`` column separated by
     newlines, which is the format expected by doorstop's LIST_SEP_RE
     splitter in doorstop/core/importer.py.
  6. Writes a UTF-8 CSV whose column order begins with the standard doorstop
     columns (uid, level, text, links, active, derived, normative, header,
     reviewed) followed by every custom column discovered across all
     requirement tables — so no data is lost and no redundant columns appear.
  7. Defaults: level="1.0", active="True", derived="False", normative="True".
  8. Validates that every requirement has a UID and reports a summary of
     parsing results to stderr.

Date extraction sources (in priority order, highest first):
  - Priority 1 (highest): Table row dates — per-requirement dates that appear
    as rows inside the two-column requirement tables (e.g. a row with label
    "Created" and a value cell containing the date string).  These take full
    priority and are never overridden by lower-priority sources.
  - Priority 2: Standalone text dates — date lines that appear outside the
    requirement tables in the HTML body, e.g.::

        Created: 02/09/2025 09:23:45 PM UTC
        Updated: 03/23/2026 06:05:49 PM UTC

    Supported labels: Created, Updated, Modified, Last Modified, Last Updated,
    Date Created, Date Modified.
  - Priority 3 (lowest): Office XML document properties — ISO 8601 dates
    stored in the MHT ``<head>`` section as Office XML tags, e.g.::

        <o:Created>2026-03-25T05:10:00Z</o:Created>
        <o:LastSaved>2026-03-25T05:11:00Z</o:LastSaved>

    These are document-level metadata and apply only when no higher-priority
    date is available for a given requirement.

Usage:
    python scripts/jama_mht_to_doorstop_csv.py input.mht -o output.csv
    python scripts/jama_mht_to_doorstop_csv.py input.mht -o output.csv --validate --verbose

Then import with doorstop::

    doorstop import output.csv YOUR_PREFIX

Requirements:
    Python >= 3.8 (standard library only — no third-party packages needed)

Arguments:
    input         Path to the .mht file exported from JAMA.
    -o/--output   Output CSV file path (default: same stem as input + .csv).
    --validate    Perform extra validation and abort on first missing UID.
    --encoding    Charset to use when decoding the base64 HTML body
                  (default: auto-detect from MIME headers, then utf-16-le).
    -v/--verbose  Enable DEBUG-level logging.
"""

from __future__ import annotations

import argparse
import base64
import csv
import email
import email.policy
import html as html_mod
import html.parser
import logging
import os
import re
import sys
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Logging – output to stderr so it doesn't mix with redirected CSV output
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    stream=sys.stderr,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Doorstop's standard columns, in preferred output order
DOORSTOP_STANDARD_COLUMNS: List[str] = [
    "uid",
    "level",
    "text",
    "links",
    "active",
    "derived",
    "normative",
    "header",
    "reviewed",
]

# Default values inserted for every row when the field was not present in JAMA
DOORSTOP_DEFAULTS: Dict[str, str] = {
    "level": "1.0",
    "active": "True",
    "derived": "False",
    "normative": "True",
}

# Mapping: normalised (underscore) JAMA label → doorstop column name.
# Keys are the result of _normalise_column_name() applied to the raw label.
JAMA_TO_DOORSTOP: Dict[str, str] = {
    "legacy_id": "uid",
    "name": "header",
    "description": "text",
    "project_id": "project_id",
    "global_id": "global_id",
    "additional_notes": "additional_notes",
    # Date fields — JAMA uses several spellings; normalise to two columns.
    "created": "created",
    "date_created": "created",
    "modified": "modified",
    "last_modified": "modified",
    "date_modified": "modified",
    "updated": "modified",
    "last_updated": "modified",
}

# JAMA field names (normalised to underscores) whose presence marks a table
# as a requirement table rather than a layout/header table.
JAMA_KNOWN_FIELDS = frozenset(
    {
        "legacy_id",
        "name",
        "description",
        "project_id",
        "global_id",
        "additional_notes",
        "status",
        "priority",
        "item_type",
        "category",
        "created",
        "date_created",
        "modified",
        "last_modified",
        "date_modified",
        "updated",
        "last_updated",
    }
)

# Matches "Parents:" (or "Parents -") followed by one or more Legacy IDs
PARENTS_RE = re.compile(
    r"Parents\s*[:\-]?\s*((?:\s*[A-Za-z][\w]*-\d+\s*)+)",
    re.IGNORECASE,
)

# Matches a single Legacy ID token (e.g. "OBJ-13", "SYS-004")
PARENT_ID_RE = re.compile(r"[A-Za-z][\w]*-\d+")

# Candidate charsets to try when decoding the base64 HTML body
_HTML_CHARSETS = ["utf-16-le", "utf-16", "utf-8", "latin-1"]

# Matches standalone date lines that appear *outside* requirement tables, e.g.:
#   "Created: 02/09/2025 09:23:45 PM UTC"
#   "Updated: 03/23/2026 06:05:49 PM UTC"
# Group 1 = label, Group 2 = date value
_STANDALONE_DATE_RE = re.compile(
    r"^(?P<label>Created|Updated|Modified|Last\s+Modified|Last\s+Updated"
    r"|Date\s+Created|Date\s+Modified)\s*:\s*(?P<value>.+)$",
    re.IGNORECASE | re.MULTILINE,
)

# Matches Office XML document-property date tags in the MHT <head>, e.g.:
#   <o:Created>2026-03-25T05:10:00Z</o:Created>
_OFFICE_CREATED_RE = re.compile(
    r"<o:Created>\s*(?P<value>[^<]+?)\s*</o:Created>",
    re.IGNORECASE,
)

# Matches Office XML last-saved date tags in the MHT <head>, e.g.:
#   <o:LastSaved>2026-03-25T05:11:00Z</o:LastSaved>
_OFFICE_LAST_SAVED_RE = re.compile(
    r"<o:LastSaved>\s*(?P<value>[^<]+?)\s*</o:LastSaved>",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Label normalisation helper  (used by parse_tables and records_to_doorstop_rows)
# ---------------------------------------------------------------------------


def _normalise_column_name(label: str) -> str:
    """Convert a JAMA field label to a safe CSV column name.

    Rules:
    - Lowercase
    - Replace runs of non-alphanumeric characters with a single underscore
    - Strip leading/trailing underscores

    Examples::

        "Legacy ID"       → "legacy_id"
        "Additional Notes" → "additional_notes"
        "Item Type"       → "item_type"
    """
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


# ---------------------------------------------------------------------------
# HTML table parser (standard library only)
# ---------------------------------------------------------------------------


class _TableParser(html.parser.HTMLParser):
    """Collect all top-level <table> elements as lists of rows.

    Each table is represented as ``List[List[str]]`` — a list of rows,
    each row being a list of cell text strings.  Nested tables (depth > 1)
    are ignored structurally; their text content still flows into the
    enclosing cell via ``handle_data``.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: List[List[List[str]]] = []

        self._table_depth: int = 0
        self._current_table: Optional[List[List[str]]] = None
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[List[str]] = None

    # ------------------------------------------------------------------
    # HTMLParser callbacks
    # ------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_table = []

        elif tag == "tr" and self._table_depth == 1:
            self._current_row = []

        elif tag in ("td", "th") and self._table_depth == 1:
            self._current_cell = []

        elif tag == "br":
            # Inline line-break inside any cell (regardless of table depth)
            if self._current_cell is not None:
                self._current_cell.append("\n")

        elif tag in ("p", "div", "li"):
            # Block-level elements: inject a newline *before* the element's
            # content if there is already some text in the cell.
            if self._current_cell is not None:
                accumulated = "".join(self._current_cell)
                if accumulated and not accumulated.endswith("\n"):
                    self._current_cell.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "table":
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                self.tables.append(self._current_table)
                self._current_table = None

        elif tag == "tr" and self._table_depth == 1:
            if self._current_row is not None and self._current_table is not None:
                if self._current_row:  # skip empty rows
                    self._current_table.append(self._current_row)
            self._current_row = None

        elif tag in ("td", "th") and self._table_depth == 1:
            if self._current_cell is not None and self._current_row is not None:
                text = "".join(self._current_cell)
                # Replace non-breaking spaces with regular spaces
                text = text.replace("\xa0", " ")
                # Strip each line and remove blank/whitespace-only lines
                lines = [ln.strip() for ln in text.split("\n")]
                text = "\n".join(ln for ln in lines if ln)
                self._current_row.append(text)
            self._current_cell = None

        elif tag in ("p", "div", "li"):
            # Inject a trailing newline after the closing block tag
            if self._current_cell is not None:
                accumulated = "".join(self._current_cell)
                if accumulated and not accumulated.endswith("\n"):
                    self._current_cell.append("\n")

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


# ---------------------------------------------------------------------------
# MHT / MIME helpers
# ---------------------------------------------------------------------------


def extract_html_from_mht(path: str, encoding: Optional[str] = None) -> str:
    """Open *path* (an MHT/MIME-HTML file) and return the decoded HTML body.

    The function tries several strategies in order:
    1. Parse as a MIME message and look for a ``text/html`` part.
    2. Fall back to locating the largest base64 block in the raw file and
       decoding it as HTML.

    :param path: path to the ``.mht`` file.
    :param encoding: explicit charset override for the base64 payload
                     (default: auto-detect from MIME headers, then utf-16-le).
    :raises ValueError: if no HTML content could be extracted.
    """
    with open(path, "rb") as fh:
        raw = fh.read()

    msg = email.message_from_bytes(raw)

    # --- Strategy 1: walk MIME parts looking for text/html ---
    if msg.is_multipart():
        for part in msg.walk():
            ct = (part.get_content_type() or "").lower()
            if "html" not in ct:
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = encoding or part.get_content_charset() or "utf-8"
            charset = _normalise_charset(charset)
            return payload.decode(charset, errors="replace")

    # --- Strategy 2: single-part with base64 transfer encoding ---
    cte = (msg.get("Content-Transfer-Encoding") or "").lower()
    if cte == "base64":
        payload = msg.get_payload(decode=True)
        if payload:
            charset = encoding or msg.get_content_charset() or "utf-16-le"
            charset = _normalise_charset(charset)
            charsets_to_try = [charset] + [
                c for c in _HTML_CHARSETS if c != charset
            ]
            for cs in charsets_to_try:
                try:
                    text = payload.decode(cs)
                    if "<html" in text.lower() or "<table" in text.lower():
                        log.info("Decoded HTML using charset '%s'.", cs)
                        return text
                except (UnicodeDecodeError, LookupError):
                    continue

    # --- Strategy 3: heuristic base64 block scan ---
    raw_text = raw.decode("ascii", errors="replace")
    b64_data = _find_base64_block(raw_text)
    if b64_data:
        charset = encoding or "utf-16-le"
        charset = _normalise_charset(charset)
        charsets_to_try = [charset] + [c for c in _HTML_CHARSETS if c != charset]
        for cs in charsets_to_try:
            try:
                decoded = base64.b64decode(b64_data)
                text = decoded.decode(cs)
                if "<html" in text.lower() or "<table" in text.lower():
                    log.info("Decoded HTML (heuristic) using charset '%s'.", cs)
                    return text
            except (UnicodeDecodeError, LookupError, Exception):
                continue

    raise ValueError(
        f"Could not extract HTML content from {path!r}. "
        "Ensure the file is a valid MHT/MIME-HTML export from JAMA."
    )


def _normalise_charset(charset: str) -> str:
    """Normalise charset aliases used by Windows/JAMA to Python codec names."""
    mapping = {
        "unicode": "utf-16-le",
        "utf-16le": "utf-16-le",
        "utf16le": "utf-16-le",
        "utf-16": "utf-16",
        "utf-8": "utf-8",
        "utf8": "utf-8",
    }
    return mapping.get(charset.lower(), charset)


def _find_base64_block(text: str) -> Optional[bytes]:
    """Heuristically locate the largest base64-encoded block in *text*.

    Returns the raw bytes of the concatenated base64 content, or ``None``
    if no block was found.
    """
    b64_chars = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    )
    blocks: List[List[str]] = []
    current: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped and len(stripped) > 20 and all(c in b64_chars for c in stripped):
            current.append(stripped)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)

    if not blocks:
        return None

    biggest = max(blocks, key=lambda b: sum(len(ln) for ln in b))
    return "".join(biggest).encode("ascii")


# ---------------------------------------------------------------------------
# HTML → records
# ---------------------------------------------------------------------------


def _extract_office_dates(html_content: str) -> Dict[str, str]:
    """Extract document-level dates from Office XML properties in *html_content*.

    Searches for ``<o:Created>`` and ``<o:LastSaved>`` tags that JAMA/Word
    embeds in the MHT ``<head>`` section and returns a dict with canonical
    doorstop column names as keys.

    :param html_content: full HTML string from the MHT file.
    :returns: dict with zero, one, or two of the keys ``"created"`` and
              ``"modified"``, mapping to the raw ISO 8601 date strings found.
    """
    result: Dict[str, str] = {}

    m = _OFFICE_CREATED_RE.search(html_content)
    if m:
        result["created"] = m.group("value")
        log.debug("Office XML: found created date: %s", result["created"])

    m = _OFFICE_LAST_SAVED_RE.search(html_content)
    if m:
        result["modified"] = m.group("value")
        log.debug("Office XML: found modified date: %s", result["modified"])

    return result


def _extract_standalone_dates(html_content: str) -> Dict[str, str]:
    """Extract per-document dates from standalone date lines in *html_content*.

    Searches for lines like ``Created: 02/09/2025 09:23:45 PM UTC`` or
    ``Updated: 03/23/2026 06:05:49 PM UTC`` that appear outside the
    requirement tables and maps their labels to canonical doorstop column
    names via :data:`JAMA_TO_DOORSTOP`.

    Only the first occurrence of each date type is kept.

    :param html_content: full HTML string from the MHT file.
    :returns: dict with zero, one, or two of the keys ``"created"`` and
              ``"modified"``, mapping to the raw date strings found.
    """
    result: Dict[str, str] = {}

    for m in _STANDALONE_DATE_RE.finditer(html_content):
        label_norm = _normalise_column_name(m.group("label"))
        canonical = JAMA_TO_DOORSTOP.get(label_norm)
        if canonical in ("created", "modified") and canonical not in result:
            result[canonical] = m.group("value").strip()
            log.debug(
                "Standalone date: label=%r → %s: %s",
                m.group("label"),
                canonical,
                result[canonical],
            )

    return result


def parse_tables(html_content: str) -> List[Dict[str, str]]:
    """Parse requirement tables from *html_content*.

    Returns a list of ``OrderedDict`` objects, one per requirement table.
    Keys are **normalised** field labels (lowercase, spaces replaced with
    underscores — the output of :func:`_normalise_column_name`).  Values are
    the cell text with HTML entities decoded and newlines preserved.

    Tables that do not contain any known JAMA field label are silently
    skipped (they are likely header/footer or layout tables).

    Date fields are filled from three sources in priority order (highest
    first):

    1. Table row dates — per-requirement dates from within the table.
    2. Standalone text dates — e.g. ``Created: 02/09/2025 09:23:45 PM UTC``
       found outside requirement tables.
    3. Office XML document properties — ``<o:Created>`` / ``<o:LastSaved>``
       tags in the MHT ``<head>`` section.
    """
    # Collect fallback dates from lower-priority sources before parsing tables.
    office_dates = _extract_office_dates(html_content)
    standalone_dates = _extract_standalone_dates(html_content)

    # Standalone dates take priority over Office XML dates.
    fallback_dates: Dict[str, str] = {**office_dates, **standalone_dates}
    if fallback_dates:
        log.debug("Fallback dates available: %s", fallback_dates)

    parser = _TableParser()
    parser.feed(html_content)
    parser.close()

    log.debug("Total <table> elements found in HTML: %d", len(parser.tables))

    records: List[Dict[str, str]] = []

    for table_idx, rows in enumerate(parser.tables):
        if not rows:
            continue

        record: Dict[str, str] = OrderedDict()
        is_requirement = False

        for row in rows:
            if len(row) < 2:
                # Single-cell row — could be a section heading; skip.
                log.debug("Table %d: skipping single-cell row: %r", table_idx, row)
                continue

            label_raw = row[0]
            value_raw = row[1]

            # Strip trailing colon (e.g. "Legacy ID:" → "Legacy ID") then
            # normalise to underscore form ("Legacy ID" → "legacy_id")
            label_stripped = re.sub(r"\s*:\s*$", "", label_raw).strip()
            if not label_stripped:
                continue
            label = _normalise_column_name(label_stripped)

            if label in JAMA_KNOWN_FIELDS:
                is_requirement = True

            # If the same label appears twice in a table, append the value
            if label in record:
                record[label] = record[label] + "\n" + value_raw
            else:
                record[label] = value_raw

        if record and is_requirement:
            # Inject fallback dates for any missing date fields.
            # A date field is considered present if any JAMA spelling variant
            # that maps to it already exists in the record.
            for canonical_date_col in ("created", "modified"):
                # Check whether any JAMA label variant for this column is
                # already in the record.
                has_date = any(
                    JAMA_TO_DOORSTOP.get(key) == canonical_date_col
                    for key in record
                )
                if not has_date and canonical_date_col in fallback_dates:
                    record[canonical_date_col] = fallback_dates[canonical_date_col]
                    log.debug(
                        "Table %d: injected fallback %s = %r",
                        table_idx,
                        canonical_date_col,
                        record[canonical_date_col],
                    )
            records.append(record)
        elif record:
            log.debug(
                "Table %d skipped (no known JAMA fields). Labels: %s",
                table_idx,
                list(record.keys()),
            )

    return records


# ---------------------------------------------------------------------------
# Records → doorstop rows
# ---------------------------------------------------------------------------


def _extract_parent_links(notes_text: str) -> List[str]:
    """Return a list of parent Legacy IDs found in *notes_text*.

    Looks for text like::

        Parents:
        OBJ-13
        OBJ-08
        OBJ-09

    and returns ``["OBJ-13", "OBJ-08", "OBJ-09"]``.
    """
    match = PARENTS_RE.search(notes_text)
    if not match:
        return []
    return PARENT_ID_RE.findall(match.group(1))


def records_to_doorstop_rows(
    records: List[Dict[str, str]],
    validate: bool = False,
) -> Tuple[List[str], List[List[str]]]:
    """Convert parsed JAMA records into doorstop-compatible CSV data.

    :param records: list of ``OrderedDict`` from :func:`parse_tables`.
    :param validate: if ``True``, abort (raise ``SystemExit``) on first record
                     missing a UID instead of just warning.
    :returns: ``(header, rows)`` where *header* is the ordered list of column
              names and *rows* is a list of value lists (one per requirement).
    """
    # -----------------------------------------------------------------------
    # Pass 1: normalise every record and discover all column names in order
    # -----------------------------------------------------------------------
    normalised_records: List[Dict[str, str]] = []
    all_custom_keys: List[str] = []  # custom keys in discovery order

    for raw_record in records:
        normed: Dict[str, str] = {}
        parent_links: List[str] = []

        for col_name, value in raw_record.items():
            # Labels are already normalised by parse_tables; look up any
            # doorstop-specific remapping (e.g. "legacy_id" → "uid").
            col_name = JAMA_TO_DOORSTOP.get(col_name, col_name)

            # "additional_notes" → extract parent links AND keep the field
            if col_name == "additional_notes":
                parent_links.extend(_extract_parent_links(value))

            if col_name in normed:
                normed[col_name] = normed[col_name] + "\n" + value
            else:
                normed[col_name] = value

            # Track custom column names (not in standard doorstop columns)
            if col_name not in DOORSTOP_STANDARD_COLUMNS and col_name not in all_custom_keys:
                all_custom_keys.append(col_name)

        # Merge extracted parent links into the "links" column
        if parent_links:
            existing_links = [
                lnk
                for lnk in normed.get("links", "").split("\n")
                if lnk.strip()
            ]
            combined: List[str] = existing_links[:]
            for lnk in parent_links:
                if lnk not in combined:
                    combined.append(lnk)
            normed["links"] = "\n".join(combined)

        normalised_records.append(normed)

    # -----------------------------------------------------------------------
    # Build the final column header
    # -----------------------------------------------------------------------
    # Always include: uid, links, and any standard column that either has a
    # default value or appears in at least one record.
    header: List[str] = []
    for col in DOORSTOP_STANDARD_COLUMNS:
        if (
            col in ("uid", "links")
            or col in DOORSTOP_DEFAULTS
            or any(col in r for r in normalised_records)
        ):
            header.append(col)

    # Ensure uid is first, links is present
    if "uid" not in header:
        header.insert(0, "uid")
    if "links" not in header:
        # Insert links after text (or after uid if text absent)
        insert_after = "text" if "text" in header else "uid"
        idx = header.index(insert_after) + 1
        header.insert(idx, "links")

    # Append custom columns in discovery order (skip any that ended up in header)
    for key in all_custom_keys:
        if key not in header:
            header.append(key)

    # -----------------------------------------------------------------------
    # Pass 2: build rows, apply defaults, validate
    # -----------------------------------------------------------------------
    rows: List[List[str]] = []
    missing_uid_count = 0
    fallback_uid_count = 0
    links_count = 0

    for idx, normed in enumerate(normalised_records):
        uid = normed.get("uid", "").strip()
        if not uid:
            # Try fallback sources in priority order before giving up:
            #   1. project_id  2. id  3. global_id
            fallback_source: str = ""
            for candidate_key in ("project_id", "id", "global_id"):
                candidate_val = normed.get(candidate_key, "").strip()
                if candidate_val:
                    fallback_source = candidate_key
                    uid = candidate_val
                    break

            if uid:
                fallback_uid_count += 1
                log.info(
                    "Record #%d has no Legacy ID; using %s '%s' as uid.",
                    idx + 1,
                    fallback_source,
                    uid,
                )
                print(
                    f"Info: Record #{idx + 1} has no Legacy ID; "
                    f"using {fallback_source} '{uid}' as uid.",
                    file=sys.stderr,
                )
                normed["uid"] = uid
            else:
                missing_uid_count += 1
                msg = (
                    f"Record #{idx + 1} has no Legacy ID, project_id, id, or global_id.  "
                    f"Record contents: {dict(normed)}"
                )
                print(f"Skipped: {msg}", file=sys.stderr)
                if validate:
                    log.error(msg)
                    raise SystemExit(1)
                log.warning(msg)
                continue

        row: List[str] = []
        for col in header:
            if col in normed:
                row.append(normed[col])
            elif col in DOORSTOP_DEFAULTS:
                row.append(DOORSTOP_DEFAULTS[col])
            else:
                row.append("")
        rows.append(row)

        if normed.get("links"):
            links_count += 1

    # -----------------------------------------------------------------------
    # Validation: check for duplicate UIDs
    # -----------------------------------------------------------------------
    uid_col_idx = header.index("uid")
    uid_counts: Dict[str, int] = {}
    for row in rows:
        u = row[uid_col_idx]
        uid_counts[u] = uid_counts.get(u, 0) + 1
    duplicates = {u: c for u, c in uid_counts.items() if c > 1}
    if duplicates:
        log.warning("Duplicate UIDs detected: %s", duplicates)

    # -----------------------------------------------------------------------
    # Summary statistics (to stderr)
    # -----------------------------------------------------------------------
    total_parsed = len(records)
    total_rows = len(rows)
    print(
        f"Summary: parsed {total_parsed} requirement table(s); "
        f"{total_rows} row(s) written; "
        f"{fallback_uid_count} used fallback id as uid; "
        f"{missing_uid_count} skipped (missing UID); "
        f"{links_count} row(s) have parent links.",
        file=sys.stderr,
    )
    if duplicates:
        print(f"Warning: duplicate UIDs: {duplicates}", file=sys.stderr)

    # Warn about completely empty columns
    for ci, col_name in enumerate(header):
        if all(row[ci] == "" for row in rows):
            log.info(
                "Column '%s' is empty for all rows "
                "(kept in output for schema consistency).",
                col_name,
            )

    return header, rows


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------


def write_csv(header: List[str], rows: List[List[str]], path: str) -> None:
    """Write *header* and *rows* to a UTF-8 CSV file at *path*."""
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
    log.info("Wrote %d data row(s) to '%s'.", len(rows), path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="jama_mht_to_doorstop_csv",
        description=(
            "Convert a JAMA-exported MHT/Word file to a doorstop-importable CSV."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Path to the .mht file exported from JAMA.")
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output CSV file path.  "
            "Defaults to the input filename with a .csv extension."
        ),
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help=(
            "Abort with a non-zero exit code if any requirement is missing a "
            "Legacy ID, rather than silently skipping it."
        ),
    )
    parser.add_argument(
        "--encoding",
        default=None,
        metavar="CHARSET",
        help=(
            "Character set used to decode the base64 HTML body "
            "(e.g. utf-16-le, utf-8).  "
            "Auto-detected from the MHT MIME headers by default; "
            "falls back to utf-16-le if not specified."
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point.  Returns an exit code (0 = success)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    input_path: str = args.input
    if not os.path.isfile(input_path):
        log.error("Input file not found: %s", input_path)
        return 1

    # Derive default output path
    output_path: str = args.output
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".csv"

    # ------------------------------------------------------------------
    # Step 1: extract HTML from the MHT envelope
    # ------------------------------------------------------------------
    log.info("Extracting HTML from '%s' …", input_path)
    try:
        html_content = extract_html_from_mht(input_path, encoding=args.encoding)
    except ValueError as exc:
        log.error("%s", exc)
        return 1

    log.debug("Extracted HTML length: %d character(s).", len(html_content))

    # ------------------------------------------------------------------
    # Step 2: parse requirement tables
    # ------------------------------------------------------------------
    log.info("Parsing requirement tables …")
    records = parse_tables(html_content)
    if not records:
        log.error(
            "No requirement tables were found in the document.  "
            "Check that the file is a valid JAMA MHT export."
        )
        return 1

    log.info("Found %d requirement table(s).", len(records))

    # ------------------------------------------------------------------
    # Step 3: convert to doorstop-compatible rows
    # ------------------------------------------------------------------
    try:
        header, rows = records_to_doorstop_rows(records, validate=args.validate)
    except SystemExit:
        return 1

    if not rows:
        log.error("No valid rows produced (all records were missing a UID).")
        return 1

    # ------------------------------------------------------------------
    # Step 4: write CSV
    # ------------------------------------------------------------------
    write_csv(header, rows, output_path)
    print(f"Output written to: {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
