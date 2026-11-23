"""Prepare a one-page release projection from independently enrolled private evidence."""
from scripts import scarb_ai_fact_slots as solo, scarb_ai_voice as voice
from scripts import scarb_notebook_release as release
from scripts.scarb_grouped_context_candidate import verify_neighbourhood_sources

TRUSTED_STAGE_SHA256 = None
STAGE_VERSION = "scarb-neighbourhood-notebook-stage-1"


def _text(value):
    return voice.plain(value, 300) and value.strip() == value


def _source_links(packet, labels):
    public_evidence = {item["id"]: item["source"] for item in packet["evidence"]
                       if item["source"].startswith("https://")}
    voice.need(isinstance(labels, dict) and labels and labels.keys() == public_evidence.keys()
               and all(_text(label) for label in labels.values()),
               "Notebook requires a label for each exact public evidence link")
    return [{"label": labels[identity], "url": url} for identity, url in public_evidence.items()]


def prepare_neighbourhood_notebook(pages, *, stage, packet, receipt, config):
    """Return the exact reviewed output and the public, receipt-free binding."""
    voice.need(isinstance(stage, dict) and TRUSTED_STAGE_SHA256 is not None
               and voice.digest(stage) == TRUSTED_STAGE_SHA256,
               "No independently approved neighbourhood notebook stage")
    voice.need(set(stage) == {"version", "area", "heading", "links", "base_sha256",
                             "output_sha256", "packet_sha256", "receipt_sha256"}
               and stage["version"] == STAGE_VERSION and _text(stage["heading"]),
               "Invalid notebook stage scope")
    area = stage["area"]
    target = release.route_path(area)
    page = pages.get(target)
    voice.need(isinstance(page, bytes) and release.digest(page) == stage["base_sha256"],
               "Notebook baseline differs")
    verify_neighbourhood_sources()

    voice.need(isinstance(packet, dict), "Notebook exact source packet is missing")
    voice.packet_check(packet)
    voice.need(voice.digest(packet) == stage["packet_sha256"]
               and packet["id"] == "notebook." + area["code"]
               and packet["surface"] == "neighbourhood" and packet["kind"] == "editorial"
               and packet["locks"].get("AREA") == area["name"] and bool(packet["locks"].get("LIMIT", "").strip()),
               "Notebook request must bind its exact area and source limitation")
    voice.need(isinstance(receipt, dict) and receipt.get("sha256") == stage["receipt_sha256"],
               "Notebook exact receipt differs")
    voice.need(isinstance(config, dict) and isinstance(config.get("author_model"), str)
               and isinstance(config.get("reviewer_model"), str)
               and config["author_model"] != config["reviewer_model"],
               "Notebook requires separate author and reviewer models")
    story = solo.receipt_check(receipt, packet, config)
    links = _source_links(packet, stage["links"])
    paragraphs = story.split("\n\n")
    _, output = release.render_page(page, area, stage["heading"], paragraphs, links)
    voice.need(release.digest(output) == stage["output_sha256"], "Notebook staged output differs")
    public = {
        "version": release.VERSION, "area": area, "heading": stage["heading"], "links": links,
        "paragraphs": paragraphs, "base_sha256": stage["base_sha256"], "output_sha256": stage["output_sha256"],
        "packet_sha256": stage["packet_sha256"], "receipt_sha256": stage["receipt_sha256"],
        "private_stage_sha256": TRUSTED_STAGE_SHA256,
    }
    return {**pages, target: output}, public


def project_neighbourhood_notebook(pages, *, stage=None, packet=None, receipt=None, config=None):
    """Keep base bytes when no stage is selected."""
    if stage is None:
        return pages
    projected, _ = prepare_neighbourhood_notebook(pages, stage=stage, packet=packet, receipt=receipt, config=config)
    return projected
