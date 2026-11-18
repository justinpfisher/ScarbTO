#!/usr/bin/env python3
"""Build a stable weekly DineSafe brief from committed, validated history.

This is a static, source-linked rendering step. It reads no live source and
publishes only events already present in the validated committed archive.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Make the repository package importable when this file is run directly by the
# publisher as ``python scripts/build_weekly_brief.py``.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.scarb_voice import weekly_intro, copy as voice_copy, compose_copy
from scripts.scarb_accepted_copy import event_explanation_or_notice, current_copy
from scripts.build_rss import EVENT_KINDS, LICENCE_URL, SOURCE_URL, FeedError, load_events, reader_date

SITE_URL = "https://scarb.to/"
BRIEFS_URL = f"{SITE_URL}briefs/"
TORONTO = "America/Toronto"
SCHEMA_VERSION = 1
BRIEF_RENDER_VERSION = 2
LINKED_RENDER_VERSION = 3
VOICE_RENDER_VERSION = 4
OFFICIAL_RECORD_URL = (
    "https://www.toronto.ca/community-people/health-wellness-care/"
    "health-programs-advice/food-safety/dinesafe/#establishment/"
)


class BriefError(ValueError):
    """Raised when committed activity cannot safely produce a weekly brief."""


def complete_week(as_of: datetime) -> tuple[date, date]:
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise BriefError("Brief reference time must include a timezone")
    try:
        local_date = as_of.astimezone(ZoneInfo(TORONTO)).date()
    except ZoneInfoNotFoundError as exc:
        raise BriefError(f"IANA timezone data is unavailable for {TORONTO}") from exc
    # The period is the most recently completed Monday-Sunday in Toronto.
    end = local_date - timedelta(days=local_date.weekday() + 1)
    return end - timedelta(days=6), end


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BriefError(f"Invalid brief control file: {path.name}") from exc
    if not isinstance(result, dict) or type(result.get("schema_version")) is not int or result["schema_version"] != SCHEMA_VERSION:
        raise BriefError(f"Invalid brief control-file envelope: {path.name}")
    return result


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise BriefError(f"Unable to write brief output {path.name}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _week_events(events: list[dict], start: date, end: date) -> list[dict]:
    try:
        tz = ZoneInfo(TORONTO)
    except ZoneInfoNotFoundError as exc:
        raise BriefError(f"IANA timezone data is unavailable for {TORONTO}") from exc
    selected = [
        event for event in events
        if start <= event["detected_at"].astimezone(tz).date() <= end
    ]
    return sorted(selected, key=lambda event: (event["detected_at"], event["id"]))


def _period_months(start: date, end: date) -> set[str]:
    months: set[str] = set()
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.add(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return months


def _content_payload(start: date, end: date, events: list[dict]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "source_url": SOURCE_URL,
        "events": [
            {
                "id": event["id"],
                "kind": event["kind"],
                "establishment_id": event["establishment_id"],
                "name": event["name"],
                "neighbourhood": event["neighbourhood"],
                "inspection_date": event["inspection_date"],
                "detected_at": event["detected_at"].isoformat(),
                "status": event["status"],
                "previous_status": event["previous_status"],
            }
            for event in events
        ],
    }


def _fmt_date(value: date) -> str:
    return reader_date(value, weekday=False)


def _official_record_url(establishment_id: object) -> str | None:
    """Return Toronto's existing exact-record destination for a valid ID."""
    if not isinstance(establishment_id, str) or not establishment_id.strip():
        return None
    # Match JavaScript encodeURIComponent used by docs/logic.mjs.
    return OFFICIAL_RECORD_URL + quote(establishment_id, safe="-_.!~*'()")


def _neighbourhood_url(name: object) -> str | None:
    """Match the canonical slug rule in docs/neighbourhood-routes.mjs."""
    if not isinstance(name, str) or not name.strip():
        return None
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(
        character for character in normalized
        if not unicodedata.category(character).startswith("M")
    )
    normalized = normalized.lower().replace("&", " and ")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return f"/{slug}/" if slug else None


def _render_edition(payload: dict, record: dict) -> bytes:
    if record.get("render_version", 1) == VOICE_RENDER_VERSION:
        return _render_voice_edition(payload, record)
    return _render_legacy_edition(payload, record)


def _render_legacy_edition(payload: dict, record: dict) -> bytes:
    render_version = record.get("render_version", 1)
    if type(render_version) is not int or render_version not in (1, BRIEF_RENDER_VERSION, LINKED_RENDER_VERSION):
        raise BriefError("Unsupported weekly-brief render version")
    start = date.fromisoformat(payload["period_start"])
    end = date.fromisoformat(payload["period_end"])
    events = payload["events"]
    kind_counts = Counter(event["kind"] for event in events)
    area_counts = Counter(event["neighbourhood"] for event in events)
    title = f"Food inspection updates: {_fmt_date(start)} to {_fmt_date(end)}"
    esc = html.escape
    rows = []
    for event in events:
        name = esc(event["name"])
        record_url = _official_record_url(event.get("establishment_id"))
        if render_version == LINKED_RENDER_VERSION and record_url:
            name = f'<a href="{esc(record_url)}">{name}</a>'
        neighbourhood = esc(event["neighbourhood"])
        area_url = _neighbourhood_url(event.get("neighbourhood"))
        if render_version == LINKED_RENDER_VERSION and area_url:
            neighbourhood = f'<a href="{esc(area_url)}">{neighbourhood}</a>'
        rows.append(
            f'<li id="event-{esc(event["id"])}">'
            f'<strong>{name}: {esc(EVENT_KINDS[event["kind"]])}</strong> '
            f'<span>({neighbourhood}; neighbourhood matched by Scarb.TO)</span> '
            f'<span>DineSafe result when added: {esc(event["status"])}.</span> '
            + (f'<span>Previous status: {esc(event["previous_status"])}.</span> ' if event["kind"] == "status_changed" and event["previous_status"] else "")
            + f'<span>Inspection date: <time datetime="{esc(event["inspection_date"])}">{reader_date(date.fromisoformat(event["inspection_date"]))}</time>.</span> '
            + f'<span>Added to Scarb.TO: <time datetime="{esc(event["detected_at"])}">{reader_date(datetime.fromisoformat(event["detected_at"]).astimezone(ZoneInfo(TORONTO)).date())}</time>.</span>'
            + f'<details><summary>Exact recording time</summary><p>I first recorded this update at {esc(event["detected_at"])}. This is not the inspection time or this page\'s publication time.</p></details>'
            + "</li>"
        )
    kinds = "".join(
        f'<li>{esc(EVENT_KINDS[kind])}: {count}</li>'
        for kind, count in sorted(kind_counts.items(), key=lambda item: EVENT_KINDS[item[0]])
    )
    areas = "".join(
        f'<li>{esc(area)}: {count}</li>'
        for area, count in sorted(area_counts.items(), key=lambda item: (item[0].casefold(), item[0]))
    )
    correction = ""
    if record["revision"] > 1:
        correction = (
            f'<aside><strong>Correction, revision {record["revision"]}:</strong> '
            f'{esc(record["correction_explanation"])} '
            f'<span>Updated {reader_date(datetime.fromisoformat(record["revised_at"]).astimezone(ZoneInfo(TORONTO)).date())}.</span></aside>'
        )
    subject_link_note = ""
    if render_version == LINKED_RENDER_VERSION:
        subject_link_note = (
            '<p>Each place name opens the City\'s current DineSafe record. '
            'It may contain newer information than the inspection date shown here.</p>\n    '
        )
    first_generated = esc(record["generated_at"])
    brand_metadata = ""
    style = "body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:auto;padding:1rem;color:#163c3c}h1,h2{line-height:1.2}li{margin:.65rem 0}a{color:#075c73}.summary{display:flex;gap:2rem;flex-wrap:wrap}aside{border-left:.25rem solid #a43;padding:.75rem;margin:1rem 0}small{color:#333}"
    site_nav = f'<nav aria-label="Site"><a href="{SITE_URL}">Scarb.TO home</a> · <a href="/briefs/">All weekly briefs</a> · <a href="/feed.xml">DineSafe RSS</a></nav>'
    if render_version in (BRIEF_RENDER_VERSION, LINKED_RENDER_VERSION):
        brand_metadata = '<meta name="theme-color" content="#0A3D2A"><link rel="icon" type="image/svg+xml" href="/assets/brand/scarbto-icon.svg">'
        style = "body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:auto;padding:1rem;color:#0A3D2A;background:#F8F5EA}h1,h2{line-height:1.2}li{margin:.65rem 0}a{color:#0F5132}.summary{display:flex;gap:2rem;flex-wrap:wrap}aside{border-left:.25rem solid #D2683C;padding:.75rem;margin:1rem 0}small{color:#42594E}.brand-header{display:flex;align-items:center;gap:1rem;min-height:72px;border-bottom:1px solid #D5DED2;margin-bottom:1rem}.brand-link{display:block;line-height:0}.brand-lockup{display:block;width:min(304px,45vw);max-height:64px;height:auto}.brand-tagline{display:none}.brand-link:focus-visible{outline:3px solid #0F5132;outline-offset:4px}@media(max-width:420px){.brand-lockup{width:64px}.brand-tagline{display:block;color:#0A3D2A;font-weight:700}}@media print{body{background:#fff;color:#000}.brand-header{break-after:avoid}}"
        site_nav = f'<header class="brand-header"><a class="brand-link" href="{SITE_URL}" aria-label="Scarb.TO home"><picture><source media="(max-width: 420px)" srcset="/assets/brand/scarbto-mark.svg"><img class="brand-lockup" src="/assets/brand/scarbto-connected.svg" alt=""></picture></a><span class="brand-tagline">Scarborough. I looked into it.</span></header><nav aria-label="Site"><a href="{SITE_URL}">Scarb.TO home</a> · <a href="/briefs/">All weekly briefs</a> · <a href="/feed.xml">DineSafe RSS</a></nav>'
    page = f'''<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Explore a week of Scarborough food inspection updates with me, with dates and City DineSafe sources to follow.">
  {brand_metadata}<link rel="canonical" href="{BRIEFS_URL}{start.isoformat()}/">
  <link rel="alternate" type="application/rss+xml" title="Scarb.TO food inspection updates" href="/feed.xml">
  <title>{esc(title)} | Scarb.TO</title>
  <style>{style}</style>
</head>
<body>
  {site_nav}
  <main>
    <h1>{esc(title)}</h1>
    <p>There's plenty to explore in Scarborough's food inspection records. I've brought together the updates I added from {_fmt_date(start)} through {_fmt_date(end)}. Start with a place you know, or follow a neighbourhood name and see what turns up.</p>
    <p>These updates come from City DineSafe records, not visits to these places. This is not a complete account of City activity, and results may have changed since.</p>
    <details><summary>Explore the week's patterns</summary><p>{len(events)} recorded updates span {len(area_counts)} neighbourhoods matched by Scarb.TO. One place can have more than one update. Here's how those records fit together.</p><p>I group each Monday-to-Sunday week using Toronto time (America/Toronto). Added dates use that same local calendar.</p>
    <div class="summary"><section><h2>What was added</h2><ul>{kinds}</ul></section><section><h2>By matched neighbourhood</h2><ul>{areas}</ul></section></div>
    <p>I match the coordinates supplied with DineSafe records to City neighbourhood boundaries. These neighbourhood assignments are made by Scarb.TO, not labels supplied by DineSafe. Inaccurate source coordinates can put a place in the wrong neighbourhood. Some of those neighbourhoods extend beyond the six Scarborough wards used to select these places. The inspection date tells you when the inspection happened; “Added to Scarb.TO” tells you when I first recorded the update, not when this page went live. A place newly added here is not necessarily a new business.</p></details><p>These are dated results, not a current safety assessment. Check the City's record before relying on an older result.</p>
    {correction}
    <h2>Explore the updates</h2>
    <ol>{''.join(rows)}</ol>
    {subject_link_note}<p>Want to follow the trail? Start with <a href="{SOURCE_URL}">City of Toronto DineSafe Open Data</a>. This brief uses information licensed under the <a href="{LICENCE_URL}">Open Government Licence – Toronto</a>.</p>
    <details><summary>How this edition was made</summary><p><small>Edition ID: {esc(record["id"])}. Revision: {record["revision"]}. First prepared: {first_generated} (UTC). Revised: {esc(record["revised_at"] or "Not revised")}. These are the edition's preparation times, not when it went live. I leave individual addresses and map coordinates out of these briefs.</small></p></details><p>I love following these records. Scarb.TO's editorial voice is AI-assisted, not first-hand reporting.</p>
  </main>
</body>
</html>
'''
    return page.encode("utf-8")

def _render_voice_edition(payload: dict, record: dict) -> bytes:
    render_version = record.get("render_version", 1)
    if type(render_version) is not int or render_version not in (VOICE_RENDER_VERSION,):
        raise BriefError("Unsupported weekly-brief render version")
    start = date.fromisoformat(payload["period_start"])
    end = date.fromisoformat(payload["period_end"])
    events = payload["events"]
    kind_counts = Counter(event["kind"] for event in events)
    area_counts = Counter(event["neighbourhood"] for event in events)
    title = compose_copy("weekly-title", {"START": _fmt_date(start), "END": _fmt_date(end)})
    esc = html.escape
    V = lambda key: esc(voice_copy(key))
    C = lambda key, fields: esc(compose_copy(key, fields))
    rows = []
    for event in events:
        name = esc(event["name"])
        record_url = _official_record_url(event.get("establishment_id"))
        if render_version == VOICE_RENDER_VERSION and record_url:
            name = f'<a href="{esc(record_url)}">{name}</a>'
        neighbourhood = esc(event["neighbourhood"])
        area_url = _neighbourhood_url(event.get("neighbourhood"))
        if render_version == VOICE_RENDER_VERSION and area_url:
            neighbourhood = f'<a href="{esc(area_url)}">{neighbourhood}</a>'
        explanation=event_explanation_or_notice({**event, "feed": "dinesafe", "source_url": SOURCE_URL})
        rows.append(
            f'<li id="event-{esc(event["id"])}">'
            f'<strong>{name}: {V(event["kind"])}</strong> '
            f'<span>({neighbourhood}{V("weekly-match-suffix")})</span> '
            f'<span>{V("weekly-result-prefix")}{esc(event["status"])}.</span> '
            + (f'<span>{V("weekly-previous-prefix")}{esc(event["previous_status"])}.</span> ' if event["kind"] == "status_changed" and event["previous_status"] else "")
            + f'<span>{V("weekly-inspection-prefix")}<time datetime="{esc(event["inspection_date"])}">{reader_date(date.fromisoformat(event["inspection_date"]))}</time>.</span> '
            + f'<span>{V("weekly-added-prefix")}<time datetime="{esc(event["detected_at"])}">{reader_date(datetime.fromisoformat(event["detected_at"]).astimezone(ZoneInfo(TORONTO)).date())}</time>.</span>'
            + f'<details><summary>{V("weekly-exact-time-label")}</summary><p>{C("weekly-recorded-at", {"TIME": event["detected_at"]})}</p></details>'
            + (f"<p>{esc(explanation)}</p>" if explanation else "")
            + "</li>"
        )
    kinds = "".join(
        f'<li>{V(kind)}: {count}</li>'
        for kind, count in sorted(kind_counts.items(), key=lambda item: EVENT_KINDS[item[0]])
    )
    areas = "".join(
        f'<li>{esc(area)}: {count}</li>'
        for area, count in sorted(area_counts.items(), key=lambda item: (item[0].casefold(), item[0]))
    )
    correction = ""
    if record["revision"] > 1:
        correction = (
            f'<aside><strong>{C("weekly-correction", {"REVISION": str(record["revision"])})}</strong> '
            f'{esc(record["correction_explanation"])} '
            f'<span>{C("weekly-updated", {"DATE": reader_date(datetime.fromisoformat(record["revised_at"]).astimezone(ZoneInfo(TORONTO)).date())})}</span></aside>'
        )
    subject_link_note = "<p>" + V("weekly-source-note") + "</p>\n    "
    first_generated = esc(record["generated_at"])
    brand_metadata = ""
    style = "body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:auto;padding:1rem;color:#163c3c}h1,h2{line-height:1.2}li{margin:.65rem 0}a{color:#075c73}.summary{display:flex;gap:2rem;flex-wrap:wrap}aside{border-left:.25rem solid #a43;padding:.75rem;margin:1rem 0}small{color:#333}"
    site_nav = f'<nav aria-label="{V("weekly-site-nav")}"><a href="{SITE_URL}">{V("weekly-home")}</a> · <a href="/briefs/">{V("weekly-all-briefs")}</a> · <a href="/feed.xml">{V("weekly-feed-link")}</a></nav>'
    if render_version in (VOICE_RENDER_VERSION,):
        brand_metadata = '<meta name="theme-color" content="#0A3D2A"><link rel="icon" type="image/svg+xml" href="/assets/brand/scarbto-icon.svg">'
        style = "body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:auto;padding:1rem;color:#0A3D2A;background:#F8F5EA}h1,h2{line-height:1.2}li{margin:.65rem 0}a{color:#0F5132}.summary{display:flex;gap:2rem;flex-wrap:wrap}aside{border-left:.25rem solid #D2683C;padding:.75rem;margin:1rem 0}small{color:#42594E}.brand-header{display:flex;align-items:center;gap:1rem;min-height:72px;border-bottom:1px solid #D5DED2;margin-bottom:1rem}.brand-link{display:block;line-height:0}.brand-lockup{display:block;width:min(304px,45vw);max-height:64px;height:auto}.brand-name{display:none}.brand-tagline{display:block}.brand-link:focus-visible{outline:3px solid #0F5132;outline-offset:4px}@media(max-width:420px){.brand-header{flex-wrap:wrap}.brand-link{display:flex;align-items:center;gap:.5rem;line-height:1.1}.brand-name{display:inline;font-weight:800;font-size:1.45rem}.brand-lockup{width:50px}.brand-tagline{display:block;color:#0A3D2A;font-weight:700}}@media print{body{background:#fff;color:#000}.brand-header{break-after:avoid}}"
        site_nav = f'<header class="brand-header"><a class="brand-link" href="{SITE_URL}" aria-label="{V("weekly-home")}"><picture><source media="(max-width: 420px)" srcset="/assets/brand/scarbto-mark.svg"><img class="brand-lockup" src="/assets/brand/scarbto-connected.svg" alt=""></picture><span class="brand-name">Scarb.TO</span></a><span class="brand-tagline">{V("weekly-tagline")}</span></header><nav aria-label="{V("weekly-site-nav")}"><a href="{SITE_URL}">{V("weekly-home")}</a> · <a href="/briefs/">{V("weekly-all-briefs")}</a> · <a href="/feed.xml">{V("weekly-feed-link")}</a></nav>'
    page = f'''<!doctype html>
<html lang="en-CA">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{V("weekly-description")}">
  {brand_metadata}<link rel="canonical" href="{BRIEFS_URL}{start.isoformat()}/">
  <link rel="alternate" type="application/rss+xml" title="{V("rss-title")}" href="/feed.xml">
  <title>{esc(title)} | Scarb.TO</title>
  <style>{style}</style>
</head>
<body>
  {site_nav}
  <main>
    <h1>{esc(title)}</h1>
    <p>{esc(weekly_intro(_fmt_date(start), _fmt_date(end)))}</p>
    <p>{V("weekly-source-limit")}</p>
    <details><summary>{V("weekly-patterns-title")}</summary><p>{C("weekly-counts", {"COUNT": str(len(events)), "AREAS": str(len(area_counts))})}</p><p>{V("weekly-timezone")}</p>
    <div class="summary"><section><h2>{V("weekly-kind-heading")}</h2><ul>{kinds}</ul></section><section><h2>{V("weekly-area-heading")}</h2><ul>{areas}</ul></section></div>
    <p>{V("weekly-geography")}</p></details><p>{V("weekly-safety")}</p>
    {correction}
    <h2>{V("weekly-updates-heading")}</h2>
    <ol>{''.join(rows)}</ol>
    {subject_link_note}<p>{V("weekly-source-invitation")}<a href="{SOURCE_URL}">{V("weekly-source-name")}</a>{V("weekly-licence-prefix")}<a href="{LICENCE_URL}">Open Government Licence – Toronto</a>.</p>
    <details><summary>{V("weekly-made-title")}</summary><p><small>{C("weekly-preparation", {"ID": record["id"], "REVISION": str(record["revision"]), "FIRST": record["generated_at"], "REVISED": record["revised_at"] or voice_copy("weekly-not-revised")})}</small></p></details><p>{V("weekly-disclosure")}</p>
  </main>
</body>
</html>
'''
    return page.encode("utf-8")


def _render_index(manifest: dict, current_start: date, current_end: date, has_current: bool) -> bytes:
    V = lambda key: html.escape(voice_copy(key))
    C = lambda key, fields: html.escape(compose_copy(key, fields))
    entries = sorted(manifest["editions"], key=lambda item: item["period_start"], reverse=True)
    links = "".join(
        f'<li><a href="/{esc_path(item["path"])}">{C("index-row-title", {"START": _fmt_date(date.fromisoformat(item["period_start"])), "END": _fmt_date(date.fromisoformat(item["period_end"]))})}</a>'
        f' <span>{C("index-row-meta", {"COUNT": str(item["event_count"]), "REVISION": str(item["revision"])})}</span></li>'
        for item in entries
    )
    if not has_current:
        quiet = f'<p>{C("index-quiet", {"START": _fmt_date(current_start), "END": _fmt_date(current_end)})}</p>'
    else:
        quiet = ""
    page = f'''<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#0A3D2A"><link rel="icon" type="image/svg+xml" href="/assets/brand/scarbto-icon.svg"><title>{V("index-title")} | Scarb.TO</title><style>body{{font:1rem/1.55 system-ui,sans-serif;max-width:60rem;margin:auto;padding:1rem;color:#0A3D2A;background:#F8F5EA}}a{{color:#0F5132}}li{{margin:.75rem 0}}.brand-header{{display:flex;align-items:center;gap:1rem;min-height:72px;border-bottom:1px solid #D5DED2;margin-bottom:1rem}}.brand-link{{display:block;line-height:0}}.brand-lockup{{display:block;width:min(304px,45vw);max-height:64px;height:auto}}.brand-tagline{{display:block;color:#0A3D2A;font-weight:700;font-size:.85rem}}.brand-name{{display:none}}.brand-link:focus-visible{{outline:3px solid #0F5132;outline-offset:4px}}@media(max-width:420px){{.brand-header{{flex-wrap:wrap}}.brand-link{{display:flex;align-items:center;gap:.5rem;line-height:1.1}}.brand-lockup{{width:50px}}.brand-name{{display:inline;color:#0A3D2A;font-size:1.45rem;font-weight:800}}.brand-tagline{{flex-basis:100%}}}}</style></head>
<body><header class="brand-header"><a class="brand-link" href="{SITE_URL}" aria-label="{V("weekly-home")}"><picture><source media="(max-width: 420px)" srcset="/assets/brand/scarbto-mark.svg"><img class="brand-lockup" src="/assets/brand/scarbto-connected.svg" alt=""></picture><span class="brand-name">Scarb.TO</span></a><span class="brand-tagline">{V("weekly-tagline")}</span></header><nav aria-label="{V("weekly-site-nav")}"><a href="{SITE_URL}">{V("weekly-home")}</a> · <a href="/feed.xml">{V("weekly-feed-link")}</a></nav><main data-scarb-period-start="{current_start.isoformat()}" data-scarb-period-end="{current_end.isoformat()}" data-scarb-has-current="{str(has_current).lower()}"><h1 data-scarb-voice="briefs-title">{html.escape(current_copy('static.briefs-title', "The week's food inspection paper trail."))}</h1><p data-scarb-voice="briefs-intro">{html.escape(current_copy('static.briefs-intro', "I love seeing how one week's DineSafe records fit together. Pick an edition and follow the inspection dates, neighbourhood connections and original source links. A quiet week in these records isn't proof that nothing happened, and I only publish a brief when there are updates to share."))}</p>{quiet}<h2>{V("index-choose")}</h2><ul>{links}</ul></main></body></html>
'''
    return page.encode("utf-8")


def esc_path(value: str) -> str:
    if not isinstance(value, str) or value.startswith("/") or ".." in Path(value).parts or not value.startswith("briefs/"):
        raise BriefError("Unsafe weekly-brief path in manifest")
    return html.escape(value)


def _validate_manifest(value: dict) -> None:
    if not isinstance(value.get("editions"), list):
        raise BriefError("Invalid weekly-brief edition registry")
    ids: set[str] = set()
    paths: set[str] = set()
    for item in value["editions"]:
        if not isinstance(item, dict):
            raise BriefError("Invalid weekly-brief edition record")
        render_version = item.get("render_version", 1)
        if type(render_version) is not int or render_version not in (1, BRIEF_RENDER_VERSION, LINKED_RENDER_VERSION, VOICE_RENDER_VERSION):
            raise BriefError("Unsupported weekly-brief render version")
        edition_id = item.get("id")
        path = item.get("path")
        if not isinstance(edition_id, str) or edition_id in ids:
            raise BriefError("Duplicate or invalid weekly-brief edition ID")
        if not isinstance(path, str) or path in paths:
            raise BriefError("Duplicate or invalid weekly-brief path")
        esc_path(path)
        if type(item.get("revision")) is not int or item["revision"] < 1:
            raise BriefError("Invalid weekly-brief revision")
        if not _is_sha256(item.get("content_sha256")):
            raise BriefError("Invalid weekly-brief content hash")
        if not _is_sha256(item.get("html_sha256")):
            raise BriefError("Invalid weekly-brief page hash")
        if not isinstance(item.get("generated_at"), str):
            raise BriefError("Missing original brief generation time")
        try:
            start = date.fromisoformat(item["period_start"])
            end = date.fromisoformat(item["period_end"])
        except (TypeError, ValueError) as exc:
            raise BriefError("Invalid weekly-brief period") from exc
        if end != start + timedelta(days=6) or item["id"] != f"dinesafe-weekly-{start.isoformat()}" or item["path"] != f"briefs/{start.isoformat()}/":
            raise BriefError("Weekly-brief registry ID/path does not match its Monday-Sunday period")
        ids.add(edition_id)
        paths.add(path)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _correction_record(existing: dict, correction: object, *, generated_at: str, content_hash: str, event_count: int) -> dict:
    if not isinstance(correction, dict):
        raise BriefError("Published edition content or wording changed; an explained correction is required")
    if type(correction.get("revision")) is not int or correction["revision"] != existing["revision"] + 1:
        raise BriefError("Correction revision must increment the published edition by exactly one")
    explanation = correction.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip() or len(explanation.strip()) > 500:
        raise BriefError("Correction requires a concise explanation of at most 500 characters")
    record = dict(existing)
    record.update({
        "revision": correction["revision"],
        "revised_at": generated_at,
        "correction_explanation": " ".join(explanation.split()),
        "event_count": event_count,
        "content_sha256": content_hash,
    })
    return record


def _reviewed_render(existing: dict, payload: dict, correction: object, generated_at: str) -> tuple[dict, bytes]:
    """Never silently replace published bytes, including copy-only changes."""
    content_hash = _sha256(_canonical_bytes(payload))
    unchanged_bytes = _render_edition(payload, existing)
    if content_hash == existing["content_sha256"] and _sha256(unchanged_bytes) == existing["html_sha256"]:
        if correction is not None and (
            not isinstance(correction, dict)
            or correction.get("revision") != existing["revision"]
            or " ".join(str(correction.get("explanation", "")).split()) != existing["correction_explanation"]
        ):
            raise BriefError("Correction does not change the published edition content or wording")
        return dict(existing), unchanged_bytes
    record = _correction_record(
        existing, correction, generated_at=generated_at,
        content_hash=content_hash, event_count=len(payload["events"]),
    )
    rendered = _render_edition(payload, record)
    record["html_sha256"] = _sha256(rendered)
    return record, rendered


def build_weekly_brief(
    history_dir: Path,
    output_dir: Path,
    corrections_path: Path,
    *,
    as_of: datetime | None = None,
) -> int:
    as_of = as_of or datetime.now(timezone.utc)
    start, end = complete_week(as_of)
    try:
        events = load_events(history_dir)
    except FeedError as exc:
        raise BriefError(str(exc)) from exc
    current_events = _week_events(events, start, end)
    payload = _content_payload(start, end, current_events)
    content_hash = _sha256(_canonical_bytes(payload))

    manifest_path = output_dir / "editions.json"
    corrections = _read_json(corrections_path, {"schema_version": SCHEMA_VERSION, "corrections": {}})
    if not isinstance(corrections.get("corrections", {}), dict):
        raise BriefError("Invalid weekly-brief correction map")
    manifest = _read_json(manifest_path, {"schema_version": SCHEMA_VERSION, "editions": []})
    _validate_manifest(manifest)
    editions = list(manifest["editions"])
    # Every registered page is published, including older unchanged editions.
    # Verify all archived bytes before any correction or edition is written.
    for prior in editions:
        prior_output = output_dir / prior["period_start"] / "index.html"
        if not prior_output.is_file() or _sha256(prior_output.read_bytes()) != prior["html_sha256"]:
            raise BriefError(f"Published weekly-brief page for {prior['id']} differs from its registry hash")
    available_months = {path.stem for path in history_dir.glob("*.json")}
    edition_id = f"dinesafe-weekly-{start.isoformat()}"
    path_rel = f"briefs/{start.isoformat()}/"
    output_path = output_dir / start.isoformat() / "index.html"
    existing = next((item for item in editions if item["id"] == edition_id), None)
    generated_at = as_of.astimezone(timezone.utc).isoformat()
    pending_pages: list[tuple[Path, bytes]] = []

    # Explicit corrections can target older editions while their complete
    # source-month archives remain in the validated history window.
    for prior in list(editions):
        prior_id = prior["id"]
        if prior_id == edition_id or prior_id not in corrections["corrections"]:
            continue
        prior_start = date.fromisoformat(prior["period_start"])
        prior_end = date.fromisoformat(prior["period_end"])
        if not _period_months(prior_start, prior_end).issubset(available_months):
            raise BriefError(f"Cannot correct {prior_id}: complete source-month archives are no longer available")
        prior_events = _week_events(events, prior_start, prior_end)
        prior_payload = _content_payload(prior_start, prior_end, prior_events)
        prior_correction = corrections["corrections"][prior_id]
        prior_output = output_dir / prior_start.isoformat() / "index.html"
        if not prior_output.is_file() or _sha256(prior_output.read_bytes()) != prior["html_sha256"]:
            raise BriefError(f"Published weekly-brief page for {prior_id} differs from its registry hash")
        revised, revised_bytes = _reviewed_render(prior, prior_payload, prior_correction, generated_at)
        pending_pages.append((prior_output, revised_bytes))
        editions = [revised if item["id"] == prior_id else item for item in editions]
    if current_events:
        if existing is None:
            if output_path.exists():
                raise BriefError("Weekly-brief page exists without its registry record; refusing to overwrite")
            correction = corrections["corrections"].get(edition_id)
            if correction is not None:
                raise BriefError("A first edition cannot be initialized from a correction record")
            record = {
                "id": edition_id,
                "path": path_rel,
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "revision": 1,
                "render_version": VOICE_RENDER_VERSION,
                "generated_at": generated_at,
                "revised_at": None,
                "correction_explanation": None,
                "event_count": len(current_events),
                "content_sha256": content_hash,
            }
        else:
            if existing.get("period_start") != start.isoformat() or existing.get("period_end") != end.isoformat() or existing.get("path") != path_rel:
                raise BriefError("Weekly-brief registry period/path mismatch")
            if not output_path.is_file():
                raise BriefError("Published weekly-brief page is missing; refusing silent recreation")
            old_page = output_path.read_bytes()
            if _sha256(old_page) != existing["html_sha256"]:
                raise BriefError("Published weekly-brief page differs from its registry hash")
            record, _ = _reviewed_render(existing, payload, corrections["corrections"].get(edition_id), generated_at)
    elif existing is not None:
        if not output_path.is_file() or _sha256(output_path.read_bytes()) != existing["html_sha256"]:
            raise BriefError("Published weekly-brief page differs from its registry hash")
        record, _ = _reviewed_render(existing, payload, corrections["corrections"].get(edition_id), generated_at)
    else:
        record = None

    if record is not None:
        page_bytes = _render_edition(payload, record)
        record["html_sha256"] = _sha256(page_bytes)
        if existing is None:
            editions.append(record)
        else:
            editions = [record if item["id"] == edition_id else item for item in editions]
        pending_pages.append((output_path, page_bytes))

    next_manifest = {"schema_version": SCHEMA_VERSION, "editions": sorted(editions, key=lambda item: item["period_start"])}
    _validate_manifest(next_manifest)
    # Finish every semantic/integrity check before changing any published file.
    for pending_path, pending_bytes in pending_pages:
        _write_atomic(pending_path, pending_bytes)
    _write_atomic(manifest_path, json.dumps(next_manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    _write_atomic(output_dir / "index.html", _render_index(next_manifest, start, end, bool(current_events)))
    return len(current_events)


def preserve_weekly_archive(output_dir: Path) -> int:
    """Verify issued editions without asserting coverage for a new week.

    A code-only publication has no new collection/coverage evidence. Neither
    the wall clock nor the newest recorded event proves a complete source week.
    Preserve every archived byte, including the index and correction controls.
    """
    manifest = _read_json(output_dir / "editions.json", {"schema_version": SCHEMA_VERSION, "editions": []})
    _validate_manifest(manifest)
    registered = set()
    if manifest["editions"] and not (output_dir / "index.html").is_file():
        raise BriefError("Published weekly-brief index is missing; refusing silent recreation")
    for edition in manifest["editions"]:
        page = output_dir / edition["period_start"] / "index.html"
        registered.add(page)
        if not page.is_file() or _sha256(page.read_bytes()) != edition["html_sha256"]:
            raise BriefError(f"Published weekly-brief page for {edition['id']} differs from its registry hash")
    if any(page not in registered for page in output_dir.glob("*/index.html")):
        raise BriefError("Weekly-brief page exists without its registry record; refusing to preserve an unverified edition")
    return len(manifest["editions"])


def main(argv: list[str] | None = None) -> int:
    root = ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-dir", type=Path, default=root / "docs" / "data" / "history")
    parser.add_argument("--output-dir", type=Path, default=root / "docs" / "briefs")
    parser.add_argument("--corrections", type=Path, default=root / "docs" / "briefs" / "corrections.json")
    parser.add_argument("--preserve-archive", action="store_true", help="Verify and retain issued editions unchanged; do not infer a new or quiet week from retained data")
    args = parser.parse_args(argv)
    try:
        if args.preserve_archive:
            count = preserve_weekly_archive(args.output_dir)
            if count:
                print(f"Code-only publication: retained {count} verified archived weekly edition(s) unchanged. No new reporting week was assessed.")
            else:
                print("Code-only publication: no verified archived weekly edition is available. No new reporting week was assessed or edition created.")
            return 0
        count = build_weekly_brief(args.history_dir, args.output_dir, args.corrections)
    except BriefError as exc:
        print(f"WEEKLY BRIEF NOT BUILT: {exc}", file=sys.stderr)
        return 2
    if count:
        print(f"Weekly DineSafe brief includes {count} validated observations for the last complete Toronto week.")
    else:
        print("I have no DineSafe updates to share for the last complete Toronto week; no edition created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
