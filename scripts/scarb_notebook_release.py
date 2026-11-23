"""Apply one independently attested Notebook projection in the Pages checkout."""
from hashlib import sha256
from html import escape, unescape
import json
import re
from urllib.parse import urlsplit

CLAIM = "[scarb-stage:neighbourhood-notebook-v1]"
MANIFEST = "scripts/scarb-notebook-projection.json"
VERSION = "scarb-notebook-public-projection-1"
FOOTER = b'    <footer class="page-footer">'
TITLE_ID = "scarb-notebook-title"
RESOLVER = "scripts/resolve_staged_release.py"
HELPER = "scripts/scarb_notebook_release.py"
WORKFLOW = ".github/workflows/refresh-and-publish.yml"
VERIFIER = "scripts/verify_code_only_release.py"
DIRECTORY = "docs/neighbourhoods/index.html"
TEST = "tests/test_scarb_notebook_release.py"
ALLOWED_CHANGES = {RESOLVER, MANIFEST, HELPER, WORKFLOW, TEST}
PINNED_FILES = {HELPER, MANIFEST, WORKFLOW, VERIFIER, DIRECTORY}
MAX_MANIFEST_BYTES = 32_768


class NotebookError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise NotebookError(message)


def digest(raw):
    return sha256(raw).hexdigest()


def hex_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value)


def exact_text(value, maximum):
    return isinstance(value, str) and 0 < len(value) <= maximum and value.strip() == value


def route_path(area):
    require(isinstance(area, dict) and area.keys() == {"code", "name", "slug"}
            and all(exact_text(value, 300) for value in area.values())
            and re.fullmatch(r"\d{3}", area["code"])
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", area["slug"])
            and area["slug"] not in {"briefs", "data", "community-data", "neighbourhoods"},
            "Invalid Notebook geography")
    return f'docs/{area["slug"]}/index.html'


def render_page(page, area, heading, paragraphs, links):
    target = route_path(area)
    require(isinstance(page, bytes), "Notebook baseline is missing")
    names = re.findall(rb'<h1 id="page-title">([^<]+)</h1>', page)
    canonical = f'<link rel="canonical" href="https://scarb.to/{area["slug"]}/">'.encode()
    marker = f'data-area-code="{area["code"]}" data-neighbourhood-page'.encode()
    require(len(names) == 1 and unescape(names[0].decode()) == area["name"]
            and page.count(canonical) == page.count(marker) == page.count(FOOTER) == 1
            and TITLE_ID.encode() not in page, "Notebook requires the matching canonical page")
    require(exact_text(heading, 300) and isinstance(paragraphs, list) and paragraphs
            and all(exact_text(text, 4000) for text in paragraphs), "Invalid Notebook story text")
    require(isinstance(links, list) and links, "Notebook source links are missing")
    items = []
    for link in links:
        require(isinstance(link, dict) and link.keys() == {"label", "url"}
                and exact_text(link["label"], 300) and exact_text(link["url"], 2000)
                and not re.search(r"[\s\\]", link["url"]), "Invalid Notebook source link")
        url = urlsplit(link["url"])
        require(url.scheme == "https" and url.hostname and not url.username and not url.password,
                "Invalid Notebook source link")
        items.append(f'<li><a href="{escape(link["url"], quote=True)}">{escape(link["label"])}</a></li>')
    body = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
    article = (f'    <article class="panel" aria-labelledby="{TITLE_ID}" style="margin-block-start:1rem">'
               f'<p class="eyebrow">Scarb\u2019s notebook</p><h2 id="{TITLE_ID}">{escape(heading)}</h2>'
               f'{body}<ul class="link-list">{"".join(items)}</ul></article>\n').encode()
    return target, page.replace(FOOTER, article + FOOTER, 1)


def load_projection(repo, sha):
    """Read only an exact reviewed artifact; authoring receipts remain private."""
    path = repo / MANIFEST
    if sha is None:
        require(not path.exists() and not path.is_symlink(), "Notebook stage has no independent approval")
        return None
    require(hex_digest(sha) and path.is_file() and path.resolve() == repo.resolve() / MANIFEST
            and not path.is_symlink() and path.stat().st_size <= MAX_MANIFEST_BYTES,
            "Missing or invalid approved Notebook projection")
    raw = path.read_bytes()
    require(digest(raw) == sha, "Approved Notebook projection bytes differ")
    value = json.loads(raw)
    seals = {"base_sha256", "output_sha256", "private_stage_sha256", "packet_sha256", "receipt_sha256"}
    require(isinstance(value, dict) and value.keys() == seals | {"version", "area", "heading", "paragraphs", "links"}
            and value["version"] == VERSION and all(hex_digest(value[key]) for key in seals),
            "Invalid Notebook projection bindings")
    return value


def approved_output(repo, approval, git, protected_trees):
    # Every publication starts from generated base pages. Only this step may add
    # the Notebook; never serve an already inserted story as an unmarked fallback.
    for path in (repo / "docs").glob("*/index.html"):
        require(TITLE_ID.encode() not in path.read_bytes(), "Notebook markup already present in a base page")
    if approval is None:
        load_projection(repo, None)
        return None
    require(isinstance(approval, dict) and approval.keys() == {"base", "sha256", "projection", "changed"}
            and hex_digest(approval["sha256"]), "Invalid Notebook release approval")
    value = load_projection(repo, approval["sha256"])
    target = route_path(value["area"])
    path = repo / target
    require(path.is_file() and not path.is_symlink() and path.resolve() == repo.resolve() / target,
            "Notebook target is not a canonical file")
    link = f'href="/{value["area"]["slug"]}/"'.encode()
    require((repo / DIRECTORY).read_bytes().count(link) == 1, "Notebook target is absent from the qualified directory")
    page = path.read_bytes()
    require(digest(page) == value["base_sha256"], "Notebook baseline bytes differ")
    _, output = render_page(page, value["area"], value["heading"], value["paragraphs"], value["links"])
    require(digest(output) == value["output_sha256"], "Notebook output bytes differ")

    # The reviewed artifact survives later ordinary publications. Authenticate
    # its original installation against the pinned single-parent release.
    activation = git(repo, "log", "-1", "--format=%H", "--", MANIFEST)
    require(re.fullmatch(r"[a-f0-9]{40}", activation)
            and git(repo, "rev-list", "--parents", "-n", "1", activation) == f'{activation} {approval["base"]}'
            and git(repo, "show", "-s", "--format=%s", activation).startswith(CLAIM + " "),
            "Notebook projection was not installed by its exact staged push")
    changed = set(git(repo, "diff", "--name-only", "--no-renames", approval["base"], activation).splitlines())
    require({MANIFEST, RESOLVER} <= changed <= ALLOWED_CHANGES and changed == approval["changed"],
            "Notebook stage has unexpected accompanying changes")
    projection = approval["projection"]
    require(PINNED_FILES | {target} <= projection.keys()
            and changed - {RESOLVER} <= projection.keys()
            and all(git(repo, "ls-tree", activation, "--", name) == f"100644 blob {blob}\t{name}"
                    for name, blob in projection.items()),
            "Notebook activation bytes differ from independent approval")
    require(all(git(repo, "rev-parse", f"{activation}:{tree}") == pin for tree, pin in protected_trees.items()),
            "Notebook activation modified protected data or archives")
    return activation, path, output
