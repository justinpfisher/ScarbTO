"""Optional single-page notebook projection. The publisher does not call it."""
from hashlib import sha256
from html import escape, unescape
import re
from urllib.parse import urlsplit

from scripts import scarb_ai_fact_slots as solo, scarb_ai_voice as voice
from scripts.scarb_grouped_context_candidate import verify_neighbourhood_sources

TRUSTED_STAGE_SHA256 = None
STAGE_VERSION = "scarb-neighbourhood-notebook-stage-1"
FOOTER = b'    <footer class="page-footer">'
TITLE_ID = "scarb-notebook-title"


def _sha(value):
    return sha256(value).hexdigest()


def _text(value):
    return voice.plain(value, 300) and value.strip() == value


def _source_links(packet, labels):
    public_evidence = {item["id"]: item["source"] for item in packet["evidence"]
                       if item["source"].startswith("https://")}
    voice.need(isinstance(labels, dict) and labels and labels.keys() == public_evidence.keys()
               and all(_text(label) for label in labels.values()),
               "Notebook requires a label for each exact public evidence link")
    links = []
    for identity, href in public_evidence.items():
        parsed = urlsplit(href)
        voice.need(parsed.scheme == "https" and parsed.hostname and not parsed.username
                   and not parsed.password and not re.search(r"[\s\\]", href),
                   "Invalid notebook source link")
        links.append(f'<li><a href="{escape(href, quote=True)}">{escape(labels[identity])}</a></li>')
    return "".join(links)


def project_neighbourhood_notebook(pages, *, stage=None, packet=None, receipt=None, config=None):
    """Keep base bytes unless an explicitly enrolled exact one-story stage is supplied."""
    if stage is None:
        return pages
    voice.need(TRUSTED_STAGE_SHA256 is not None and voice.digest(stage) == TRUSTED_STAGE_SHA256,
               "No independently approved neighbourhood notebook stage")
    voice.need(set(stage) == {"version", "area", "heading", "links", "base_sha256",
                             "output_sha256", "packet_sha256", "receipt_sha256"}
               and stage["version"] == STAGE_VERSION and _text(stage["heading"]),
               "Invalid notebook stage scope")
    area = stage["area"]
    voice.need(isinstance(area, dict) and set(area) == {"code", "name", "slug"}
               and all(_text(value) for value in area.values())
               and re.fullmatch(r"\d{3}", area["code"]) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", area["slug"]),
               "Invalid notebook geography")
    target = f'docs/{area["slug"]}/index.html'
    page = pages.get(target)
    voice.need(isinstance(page, bytes) and _sha(page) == stage["base_sha256"],
               "Notebook baseline differs")
    verify_neighbourhood_sources()
    name_match = re.findall(rb'<h1 id="page-title">([^<]+)</h1>', page)
    canonical = f'<link rel="canonical" href="https://scarb.to/{area["slug"]}/">'.encode("utf-8")
    area_marker = f'data-area-code="{area["code"]}" data-neighbourhood-page'.encode("utf-8")
    voice.need(len(name_match) == 1 and unescape(name_match[0].decode("utf-8")) == area["name"]
               and page.count(canonical) == page.count(area_marker) == page.count(FOOTER) == 1
               and TITLE_ID.encode("utf-8") not in page, "Notebook requires the matching canonical neighbourhood page")

    voice.packet_check(packet)
    voice.need(voice.digest(packet) == stage["packet_sha256"]
               and packet["id"] == "notebook." + area["code"]
               and packet["surface"] == "neighbourhood" and packet["kind"] == "editorial"
               and packet["locks"].get("AREA") == area["name"] and bool(packet["locks"].get("LIMIT", "").strip()),
               "Notebook request must bind its exact area and source limitation")
    voice.need(isinstance(receipt, dict) and receipt.get("sha256") == stage["receipt_sha256"],
               "Notebook exact receipt differs")
    story = solo.receipt_check(receipt, packet, config)
    links = _source_links(packet, stage["links"])
    paragraphs = story.split("\n\n")
    voice.need(all(paragraph.strip() for paragraph in paragraphs),
               "Notebook story has an empty paragraph")
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
    article = (f'    <article class="panel" aria-labelledby="{TITLE_ID}">'
               f'<p class="eyebrow">Scarb\u2019s notebook</p><h2 id="{TITLE_ID}">{escape(stage["heading"])}</h2>'
               f'{body}<ul class="link-list">{links}</ul></article>\n').encode("utf-8")
    projected = page.replace(FOOTER, article + FOOTER, 1)
    voice.need(_sha(projected) == stage["output_sha256"], "Notebook staged output differs")
    return {**pages, target: projected}
