"""YouTube notebook-update check — @energiaenergy, official channel only.

USER RULES (2026-11-10, explicit — these are requirements, not hints):

1. ONE-TIME ONLY. This check runs ONLY ONCE and ONLY at install /
   update time of the system. It is NOT a continuous or periodic
   review. There is no review interval on purpose. Enforcement: a
   marker file is written after the first run; later calls return
   ``status="already_ran"`` without touching the network, unless the
   caller passes ``force=True`` — and ``force`` is reserved for an
   explicit install/update run.
2. OFFICIAL CHANNEL ONLY. Only updates from the OFFICIAL repositories
   published on César's own YouTube channel (@energiaenergy) are
   admitted. The source of truth is the channel's public RSS feed —
   no API key, no OAuth, no login.
3. REJECT MODIFIED COPIES. The system CANNOT admit a modified copy
   that is not found on his YouTube channel. If a notebook
   publication is a modified copy that does not appear on the channel,
   it must be rejected. The user's reason: the official channel
   repositories apparently cannot be modified by third parties, so
   they are the trusted source; the problem would be modified copies
   outside the channel.

The channel ID (``UC...``) was NOT resolved by this agent: the public
channel page's text extraction exposes no ID, the legacy
``?user=energiaenergy`` feed returns 404, and the handle→ID lookup
service was unreachable from this environment. The ID is therefore a
configuration value (:attr:`OptimizationConfig.youtube_channel_id`).
Fill it from YouTube Studio → Settings → Channel → Advanced
settings, or channel page → …more → Share channel → Copy channel ID.
Until it is set, :func:`check_youtube_updates` refuses to run and
says so plainly instead of guessing.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

RSS_FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
MARKER_FILENAME = "youtube_updates.done.json"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
# Fallback namespace used by some feed readers for media descriptions.
MEDIA_NS = "{http://search.yahoo.com/mrss/}"


def feed_url(channel_id: str) -> str:
    """Public RSS feed URL for a channel ID. No key, no OAuth."""
    return RSS_FEED_URL.format(channel_id=channel_id)


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def parse_feed(xml_text: str) -> list:
    """Parse a YouTube Atom feed into a list of entries.

    Each entry: ``{"video_id", "title", "link", "published", "summary"}``.
    Malformed XML returns an empty list instead of raising.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    entries = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        video_id = ""
        link = ""
        title = ""
        published = ""
        summary = ""
        id_el = entry.find(f"{ATOM_NS}id")
        if id_el is not None and id_el.text:
            video_id = id_el.text.rsplit(":", 1)[-1]
        link_el = entry.find(f"{ATOM_NS}link")
        if link_el is not None:
            link = link_el.get("href", "")
        title_el = entry.find(f"{ATOM_NS}title")
        if title_el is not None and title_el.text:
            title = title_el.text
        pub_el = entry.find(f"{ATOM_NS}published")
        if pub_el is not None and pub_el.text:
            published = pub_el.text
        group = entry.find(f"{MEDIA_NS}group")
        if group is not None:
            desc = group.find(f"{MEDIA_NS}description")
            if desc is not None and desc.text:
                summary = desc.text
        entries.append(
            {
                "video_id": video_id,
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
            }
        )
    return entries


def filter_entries(entries: list, keywords: list) -> list:
    """Keep only entries whose title/summary matches a keyword.

    Keywords are matched case-insensitively as substrings, so
    "notebook" also matches "notebooks". Empty keyword list = keep all.
    """
    if not keywords:
        return list(entries)
    wanted = [_normalize(k) for k in keywords if k]
    kept = []
    for entry in entries or []:
        haystack = _normalize(entry.get("title", "") + " " + entry.get("summary", ""))
        if any(word in haystack for word in wanted):
            kept.append(entry)
    return kept


def admit_update(candidate: dict, feed_entries: list) -> dict:
    """Admit or reject a candidate notebook update — rule 3 enforced.

    A candidate is admitted ONLY if it matches an entry of the
    official channel feed, by video URL or by normalized title. Any
    candidate that does not appear on the channel is rejected as a
    possible modified copy, whatever it claims to be.

    ``candidate``: ``{"url": ..., "title": ...}`` (either key may be
    missing). Returns ``{"admitted": bool, "reason": str,
    "matched_entry": dict | None}``.
    """
    feed_entries = feed_entries or []
    cand_url = (candidate or {}).get("url", "") or ""
    cand_title = _normalize((candidate or {}).get("title", "") or "")
    for entry in feed_entries:
        entry_url = entry.get("link", "") or ""
        entry_title = _normalize(entry.get("title", "") or "")
        if cand_url and entry_url and cand_url.rstrip("/") == entry_url.rstrip("/"):
            return {"admitted": True, "reason": "match by video URL on the official channel", "matched_entry": entry}
        if cand_title and entry_title and cand_title == entry_title:
            return {"admitted": True, "reason": "match by title on the official channel", "matched_entry": entry}
    return {
        "admitted": False,
        "reason": "rejected: not found on the official YouTube channel (@energiaenergy); possible modified copy",
        "matched_entry": None,
    }


def _default_fetch(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Odysseus-Optimizations/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _marker_path(state_dir: str) -> str:
    return os.path.join(state_dir, MARKER_FILENAME)


def _read_marker(state_dir: str) -> dict | None:
    path = _marker_path(state_dir)
    if not state_dir or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _write_marker(state_dir: str, payload: dict) -> None:
    if not state_dir:
        return
    os.makedirs(state_dir, exist_ok=True)
    with open(_marker_path(state_dir), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def check_youtube_updates(config, *, force: bool = False, fetcher=None) -> dict:
    """Run the one-time YouTube notebook-update check.

    - ``force=False`` (default): if a previous run's marker exists,
      return ``status="already_ran"`` without any network access.
      ``force=True`` is ONLY for an explicit install/update run.
    - Without a configured ``youtube_channel_id`` the check refuses
      to run (``status="no_channel_id"``) instead of guessing.
    - ``fetcher`` is an injectable ``url -> xml_text`` callable used
      by the tests (mocks only — no network in tests).

    Returns a dict with ``status`` (``"ok"`` / ``"already_ran"`` /
    ``"no_channel_id"`` / ``"fetch_error"``), the matched entries and
    the marker payload when one was written.
    """
    state_dir = getattr(config, "youtube_state_dir", "") or ""
    if not force:
        marker = _read_marker(state_dir) if state_dir else None
        if marker is not None:
            return {
                "status": "already_ran",
                "reason": "this check runs only once, at install/update time; it already ran on "
                + str(marker.get("ran_at", "an earlier run")),
                "marker": marker,
                "entries": [],
            }
    channel_id = (getattr(config, "youtube_channel_id", "") or "").strip()
    if not channel_id:
        return {
            "status": "no_channel_id",
            "reason": "youtube_channel_id is not configured; get it from YouTube Studio → "
            "Settings → Channel → Advanced settings (or channel page → …more → "
            "Share channel → Copy channel ID) and set OPT_YT_CHANNEL_ID",
            "entries": [],
        }
    fetch = fetcher or _default_fetch
    try:
        xml_text = fetch(feed_url(channel_id))
    except Exception as exc:  # network is best-effort; never crash the app
        return {"status": "fetch_error", "reason": str(exc), "entries": []}
    entries = filter_entries(parse_feed(xml_text), list(getattr(config, "youtube_keywords", []) or []))
    payload = {
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "channel_handle": getattr(config, "youtube_channel_handle", "@energiaenergy"),
        "channel_id": channel_id,
        "matched_entries": len(entries),
        "entries": entries,
    }
    _write_marker(state_dir, payload)
    return {"status": "ok", "reason": "one-time check completed", "entries": entries, "marker": payload}
