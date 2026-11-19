"""Deterministic Scarb-authored feed copy. Source facts remain caller-validated values."""
from scripts.scarb_accepted_copy import current_copy

VOICE_REVISION = "2026-11-17-2x"
import json
import re
from pathlib import Path
COPY = json.loads((Path(__file__).resolve().parents[1] / 'config/scarb-python-copy-drafts.json').read_text(encoding='utf-8'))

def copy(key, read=current_copy):
    if key not in COPY:
        raise ValueError("Unregistered Scarb copy: " + key)
    text = read("python." + key, COPY[key])
    pattern = r"\{\{([A-Z][A-Z0-9]*)\}\}"
    if sorted(re.findall(pattern, text)) != sorted(re.findall(pattern, COPY[key])):
        raise ValueError("Accepted copy changed factual placeholders")
    return text


def compose_copy(key, fields, read=current_copy):
    text = copy(key, read)
    names = set(re.findall(r"\{\{([A-Z][A-Z0-9]*)\}\}", text))
    if set(fields) != names or any(not isinstance(value, str) or not value for value in fields.values()):
        raise ValueError("Invalid factual copy fields")
    return re.sub(r"\{\{([A-Z][A-Z0-9]*)\}\}", lambda m: fields[m[1]], text)


def rss_description(event, *, inspection_date, observed_date):
    details = [compose_copy("rss-neighbourhood", {"NAME": event["neighbourhood"]}), copy("coordinate-limits")]
    if event["previous_status"]:
        details.append(compose_copy("rss-previous", {"STATUS": event["previous_status"]}))
    details.extend([
        compose_copy("rss-source", {"URL": event["source_url"]}),
        compose_copy("rss-result", {"STATUS": event["status"]}),
        compose_copy("rss-inspection", {"DATE": inspection_date}),
        compose_copy("rss-observed", {"DATE": observed_date}),
        copy("safety"),
    ])
    return " ".join(details)


def weekly_intro(start, end):
    return compose_copy("weekly-intro", {"START": start, "END": end})
