#!/usr/bin/env python3
"""Create a static, Git-friendly snapshot of public WordPress content."""

import argparse
import hashlib
import html
import json
import mimetypes
import os
import re
import shutil
import ssl
import unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

import certifi


DEFAULT_WORDPRESS_URL = "https://www.hkbrezno.sk"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "content" / "wordpress" / "posts.json"
PAGES_OUTPUT = ROOT / "content" / "wordpress" / "pages.json"
IMAGE_ROOT = ROOT / "public" / "images" / "articles" / "wordpress"
DOCUMENT_ROOT = ROOT / "public" / "documents" / "wordpress"
IMAGE_MIRROR = ROOT / "images" / "articles" / "wordpress"
DOCUMENT_MIRROR = ROOT / "documents" / "wordpress"
USER_AGENT = "Mozilla/5.0 (compatible; HKBreznoWordPressImporter/1.0)"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
REMOVED_BLOCKS_RE = re.compile(
    r"<(script|style|form|object|embed)\b[^>]*>.*?</\1\s*>", re.I | re.S
)
EVENT_HANDLER_RE = re.compile(r"\s+on[a-z]+\s*=\s*([\"']).*?\1", re.I | re.S)
SRCSET_RE = re.compile(r"\s+(?:srcset|sizes)\s*=\s*([\"']).*?\1", re.I | re.S)
URL_ATTR_RE = re.compile(r"(?P<prefix>\b(?:src|href)\s*=\s*['\"])(?P<url>[^'\"]+)(?P<suffix>['\"])", re.I)
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".odt"}
ALLOWED_TAGS = {
    "a", "b", "blockquote", "br", "code", "div", "em", "figcaption",
    "figure", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "li",
    "mark", "ol", "p", "pre", "span", "strong", "sub", "sup", "table",
    "tbody", "td", "th", "thead", "tr", "ul",
}
BLOCKED_TAGS = {"script", "style", "form", "object", "embed", "iframe", "template"}
VOID_TAGS = {"br", "hr", "img"}
GLOBAL_ATTRIBUTES = set()
TAG_ATTRIBUTES = {
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "title", "width", "height", "loading", "decoding"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
}


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


class ContentBlockExtractor(HTMLParser):
    """Extract editorial text blocks without carrying Elementor markup across."""

    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p"}

    def __init__(self, stop_heading=""):
        super().__init__(convert_charrefs=True)
        self.stop_heading = stop_heading.casefold()
        self.current_tag = None
        self.parts = []
        self.blocks = []
        self.stopped = False

    def handle_starttag(self, tag, attrs):
        if self.stopped:
            return
        tag = tag.lower()
        if tag in self.BLOCK_TAGS and self.current_tag is None:
            self.current_tag = tag
            self.parts = []
        elif tag == "br" and self.current_tag:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.current_tag and not self.stopped:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.stopped or tag.lower() != self.current_tag:
            return
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        value = "\n".join(line for line in lines if line).strip()
        if value and self.current_tag.startswith("h") \
                and value.casefold() == self.stop_heading:
            self.stopped = True
        elif value:
            self.blocks.append({"tag": self.current_tag, "text": value})
        self.current_tag = None
        self.parts = []


class MediaExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag.lower() == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag.lower() == "img" and values.get("src"):
            self.images.append(values["src"])


class ContentSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.blocked = []

    @staticmethod
    def safe_resource(value):
        value = html.unescape(value).strip()
        if not value:
            return ""
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("", "http", "https", "mailto", "tel"):
            return ""
        if value.startswith("//"):
            return "https:" + value
        return value

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if self.blocked:
            if tag in BLOCKED_TAGS:
                self.blocked.append(tag)
            return
        if tag in BLOCKED_TAGS:
            self.blocked.append(tag)
            return
        if tag not in ALLOWED_TAGS:
            return

        allowed = GLOBAL_ATTRIBUTES | TAG_ATTRIBUTES.get(tag, set())
        clean_attrs = []
        for name, value in attrs:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name in ("href", "src"):
                value = self.safe_resource(value)
                if not value:
                    continue
            if name == "target" and value != "_blank":
                continue
            clean_attrs.append((name, value))
        if tag == "a" and any(name == "target" for name, _ in clean_attrs):
            clean_attrs = [(name, value) for name, value in clean_attrs if name != "rel"]
            clean_attrs.append(("rel", "noopener noreferrer"))
        if tag == "img" and not any(name == "src" for name, _ in clean_attrs):
            return

        attrs_html = "".join(
            f' {name}="{html.escape(value, quote=True)}"'
            for name, value in clean_attrs
        )
        self.output.append(f"<{tag}{attrs_html}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        if tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.blocked:
            self.output.append(html.escape(data, quote=False))


def sanitize_content(value):
    sanitizer = ContentSanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return "".join(sanitizer.output).strip()


def plain_text(value):
    parser = TextExtractor()
    parser.feed(value or "")
    return html.unescape(" ".join(parser.parts)).replace("[…]", "").strip()


def shortened(value, limit=240):
    if len(value) <= limit:
        return value
    return value[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:") + "…"


def slugify(value):
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")


def previous_slugs():
    if not OUTPUT.exists():
        return {}
    try:
        data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if data.get("schemaVersion") != 2:
        return {}
    return {
        post["id"]: post["slug"]
        for post in data.get("posts", [])
        if post.get("id") and post.get("slug")
    }


def build_post_slugs(posts):
    stable = previous_slugs()
    used = set()
    slugs = {}
    for post in posts:
        title = plain_text(post.get("title", {}).get("rendered", ""))
        base = stable.get(post["id"]) or slugify(title) or f"wordpress-{post['id']}"
        slug = base if base not in used else f"{base}-{post['id']}"
        used.add(slug)
        slugs[post["id"]] = slug
    return slugs


def safe_url(url):
    parts = urlsplit(url)
    path = quote(unquote(parts.path), safe="/()@:+")
    return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))


class SameHostRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allowed_host):
        super().__init__()
        self.allowed_host = allowed_host

    def redirect_request(self, request, fp, code, msg, headers, new_url):
        target = urlsplit(new_url)
        if target.scheme != "https" or target.hostname != self.allowed_host:
            raise ValueError("Presmerovanie mimo povoleného WordPress hosta")
        return super().redirect_request(request, fp, code, msg, headers, new_url)


def fetch(url, allowed_host):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != allowed_host:
        raise ValueError("Import povoľuje iba HTTPS zdroje z WordPress hosta")
    request = Request(safe_url(url), headers={"User-Agent": USER_AGENT})
    opener = build_opener(
        HTTPSHandler(context=SSL_CONTEXT),
        SameHostRedirectHandler(allowed_host),
    )
    with opener.open(request, timeout=45) as response:
        return response.read(), response.headers.get_content_type()


def fetch_posts(wordpress_url, limit=None):
    api_url = wordpress_url.rstrip("/") + "/wp-json/wp/v2/posts"
    wordpress_host = urlsplit(wordpress_url).hostname
    if not wordpress_host:
        raise ValueError("WordPress URL nemá platný host")
    posts = []
    page = 1
    while True:
        query = urlencode({
            "status": "publish",
            "per_page": 100,
            "page": page,
            "orderby": "date",
            "order": "desc",
            "_embed": 1,
        })
        payload, _ = fetch(f"{api_url}?{query}", wordpress_host)
        batch = json.loads(payload.decode("utf-8"))
        if not isinstance(batch, list):
            raise ValueError("WordPress API nevrátilo zoznam článkov")
        posts.extend(batch)
        if len(batch) < 100 or (limit and len(posts) >= limit):
            break
        page += 1
    return posts[:limit] if limit else posts


def fetch_page(wordpress_url, slug):
    wordpress_host = urlsplit(wordpress_url).hostname
    if not wordpress_host:
        raise ValueError("WordPress URL nemá platný host")
    query = urlencode({"slug": slug, "status": "publish", "per_page": 1})
    url = wordpress_url.rstrip("/") + f"/wp-json/wp/v2/pages?{query}"
    payload, _ = fetch(url, wordpress_host)
    pages = json.loads(payload.decode("utf-8"))
    if not isinstance(pages, list):
        raise ValueError(f"WordPress API nevrátilo zoznam pre stránku {slug}")
    return pages[0] if pages else None


def embedded_terms(post, taxonomy):
    groups = post.get("_embedded", {}).get("wp:term", [])
    return [
        plain_text(term.get("name", ""))
        for group in groups
        for term in group
        if term.get("taxonomy") == taxonomy and term.get("name")
    ]


def embedded_author(post):
    authors = post.get("_embedded", {}).get("author", [])
    return plain_text(authors[0].get("name", "HK Brezno")) if authors else "HK Brezno"


def featured_image_url(post):
    media = post.get("_embedded", {}).get("wp:featuredmedia", [])
    if not media:
        return ""
    image = media[0]
    sizes = image.get("media_details", {}).get("sizes", {})
    for size in ("jnews-featured-750", "medium_large", "large"):
        if sizes.get(size, {}).get("source_url"):
            return sizes[size]["source_url"]
    return image.get("source_url", "")


def asset_extension(url, content_type):
    suffix = Path(urlsplit(url).path).suffix.lower()
    if suffix and len(suffix) <= 6:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(content_type or "") or ".bin"
    return ".jpg" if guessed == ".jpe" else guessed


def download_asset(url, directory, public_directory, stem, allowed_host):
    absolute_url = html.unescape(url)
    payload, content_type = fetch(absolute_url, allowed_host)
    extension = asset_extension(absolute_url, content_type)
    digest = hashlib.sha256(absolute_url.encode("utf-8")).hexdigest()[:8]
    filename = f"{slugify(stem) or 'asset'}-{digest}{extension}"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_bytes(payload)
    return f"/{public_directory.strip('/')}/{filename}"


def normalize_link(url):
    parts = urlsplit(html.unescape(url))
    path = parts.path.rstrip("/") + "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def mirror_body_assets(body_html, wordpress_url, slug, article_links):
    image_dir = IMAGE_ROOT / slug
    document_dir = DOCUMENT_ROOT / slug
    image_public = f"images/articles/wordpress/{slug}"
    document_public = f"documents/wordpress/{slug}"
    wordpress_host = urlsplit(wordpress_url).hostname
    mirrored = {}

    def replace_attribute(match):
        raw_url = html.unescape(match.group("url"))
        absolute_url = urljoin(wordpress_url.rstrip("/") + "/", raw_url)
        normalized = normalize_link(absolute_url)
        if match.group("prefix").lower().lstrip().startswith("href"):
            if normalized in article_links:
                replacement = f"/aktuality/{article_links[normalized]}/"
                return f"{match.group('prefix')}{replacement}{match.group('suffix')}"
            extension = Path(urlsplit(absolute_url).path).suffix.lower()
            if extension not in DOCUMENT_EXTENSIONS:
                return match.group(0)
            public_path = mirrored.get(absolute_url)
            if not public_path:
                stem = Path(urlsplit(absolute_url).path).stem or "dokument"
                public_path = download_asset(
                    absolute_url, document_dir, document_public, stem, wordpress_host
                )
                mirrored[absolute_url] = public_path
            return f"{match.group('prefix')}{public_path}{match.group('suffix')}"

        parts = urlsplit(absolute_url)
        if (parts.scheme != "https" or parts.hostname != wordpress_host
                or "/wp-content/uploads/" not in parts.path):
            return f"{match.group('prefix')}{match.group('suffix')}"
        public_path = mirrored.get(absolute_url)
        if not public_path:
            stem = Path(urlsplit(absolute_url).path).stem or "obrazok"
            public_path = download_asset(
                absolute_url, image_dir, image_public, stem, wordpress_host
            )
            mirrored[absolute_url] = public_path
        return f"{match.group('prefix')}{public_path}{match.group('suffix')}"

    cleaned = REMOVED_BLOCKS_RE.sub("", body_html or "")
    cleaned = EVENT_HANDLER_RE.sub("", cleaned)
    cleaned = SRCSET_RE.sub("", cleaned)
    mirrored_html = URL_ATTR_RE.sub(replace_attribute, cleaned).strip()
    return sanitize_content(mirrored_html)


def import_posts(wordpress_url, limit=None):
    raw_posts = fetch_posts(wordpress_url, limit)
    slugs = build_post_slugs(raw_posts)
    article_links = {
        normalize_link(post["link"]): slugs[post["id"]]
        for post in raw_posts
        if post.get("link")
    }
    imported = []

    for post in raw_posts:
        slug = slugs[post["id"]]
        cover_url = featured_image_url(post)
        cover = ""
        if cover_url:
            cover = download_asset(
                cover_url,
                IMAGE_ROOT / slug,
                f"images/articles/wordpress/{slug}",
                "cover",
                urlsplit(wordpress_url).hostname,
            )
        body_html = mirror_body_assets(
            post.get("content", {}).get("rendered", ""),
            wordpress_url,
            slug,
            article_links,
        )
        imported.append({
            "id": post["id"],
            "slug": slug,
            "date": post["date"][:10],
            "modified": post.get("modified", post["date"])[:19],
            "title": plain_text(post.get("title", {}).get("rendered", "")),
            "description": shortened(
                plain_text(post.get("excerpt", {}).get("rendered", ""))
            ),
            "cover": cover,
            "author": embedded_author(post),
            "categories": embedded_terms(post, "category"),
            "tags": embedded_terms(post, "post_tag"),
            "bodyHtml": body_html,
            "sourceUrl": post.get("link", ""),
        })

    imported.sort(key=lambda item: (item["date"], item["id"]), reverse=True)
    return imported


def extract_content_blocks(value, stop_heading=""):
    parser = ContentBlockExtractor(stop_heading=stop_heading)
    parser.feed(value or "")
    parser.close()
    return parser.blocks


def import_ice_schedule(page, wordpress_url):
    if not page:
        return {
            "title": "Rozpis ľadu",
            "modified": "",
            "sourceUrl": "",
            "asset": "",
            "assetType": "",
        }

    rendered = page.get("content", {}).get("rendered", "")
    parser = MediaExtractor()
    parser.feed(rendered)
    parser.close()
    wordpress_host = urlsplit(wordpress_url).hostname

    candidates = parser.links + parser.images
    asset_url = ""
    for candidate in candidates:
        absolute = urljoin(wordpress_url.rstrip("/") + "/", html.unescape(candidate))
        parts = urlsplit(absolute)
        if parts.scheme != "https" or parts.hostname != wordpress_host:
            continue
        if "/wp-content/uploads/" not in parts.path:
            continue
        extension = Path(parts.path).suffix.lower()
        if extension == ".pdf":
            asset_url = absolute
            break
        if not asset_url and extension in {".png", ".jpg", ".jpeg", ".webp"}:
            asset_url = absolute

    asset = ""
    asset_type = ""
    if asset_url:
        extension = Path(urlsplit(asset_url).path).suffix.lower()
        if extension == ".pdf":
            asset = download_asset(
                asset_url,
                DOCUMENT_ROOT / "rozpis-ladu",
                "documents/wordpress/rozpis-ladu",
                "rozpis-ladu",
                wordpress_host,
            )
            asset_type = "pdf"
        else:
            asset = download_asset(
                asset_url,
                IMAGE_ROOT / "rozpis-ladu",
                "images/articles/wordpress/rozpis-ladu",
                "rozpis-ladu",
                wordpress_host,
            )
            asset_type = "image"

    return {
        "title": plain_text(page.get("title", {}).get("rendered", "")) or "Rozpis ľadu",
        "modified": page.get("modified", page.get("date", ""))[:19],
        "sourceUrl": page.get("link", ""),
        "asset": asset,
        "assetType": asset_type,
    }


def import_contact(page):
    defaults = {
        "name": "Hokejový klub Brezno",
        "address": ["Štvrť Ladislava Novomeského 2157/34", "977 01 Brezno"],
        "email": "info@hkbrezno.sk",
        "companyId": "31905277",
        "taxId": "2021170558",
        "vatId": "SK2021170558",
        "registry": "Register mimovládnych neziskových organizácií Ministerstva vnútra SR",
        "registryNumber": "VVS/1-900/90-10231",
    }
    rendered = page.get("content", {}).get("rendered", "") if page else ""
    blocks = extract_content_blocks(rendered, stop_heading="Partneri")
    lines = [block["text"] for block in blocks]
    joined = "\n".join(lines)

    def first_match(pattern, fallback, flags=re.I):
        match = re.search(pattern, joined, flags)
        return match.group(1).strip() if match else fallback

    street = first_match(
        r"((?:Štvrť|Ulica|Námestie)\s+[^\n]+)", defaults["address"][0]
    )
    city = first_match(r"(\d{3}\s*\d{2}\s+Brezno)", defaults["address"][1])
    email_value = first_match(
        r"([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})", defaults["email"]
    )
    if "*" in email_value:
        email_value = defaults["email"]

    return {
        "modified": (page or {}).get("modified", "")[:19],
        "sourceUrl": (page or {}).get("link", ""),
        "name": next(
            (line for line in lines if line.casefold() == "hokejový klub brezno"),
            defaults["name"],
        ),
        "address": [street, city],
        "email": email_value,
        "companyId": first_match(r"IČO\s*\n?\s*(\d{8})", defaults["companyId"]),
        "taxId": first_match(r"DIČ\s*\n?\s*(\d{10})", defaults["taxId"]),
        "vatId": first_match(r"IČ\s*DPH\s*\n?\s*(SK\d{10})", defaults["vatId"]),
        "registry": defaults["registry"],
        "registryNumber": first_match(
            r"(VVS/\d+-\d+/\d+-\d+)", defaults["registryNumber"]
        ),
    }


def import_pages(wordpress_url):
    contact_page = fetch_page(wordpress_url, "kontakt")
    history_page = fetch_page(wordpress_url, "historia")
    ice_page = fetch_page(wordpress_url, "rozpis-ladu")

    history_html = history_page.get("content", {}).get("rendered", "") if history_page else ""
    history = {
        "modified": (history_page or {}).get("modified", "")[:19],
        "sourceUrl": (history_page or {}).get("link", ""),
        "blocks": extract_content_blocks(history_html, stop_heading="Partneri"),
    }
    contact = import_contact(contact_page)
    ice_schedule = import_ice_schedule(ice_page, wordpress_url)
    modified = [
        item for item in (
            contact["modified"], history["modified"], ice_schedule["modified"]
        ) if item
    ]
    return {
        "schemaVersion": 1,
        "source": wordpress_url.rstrip("/"),
        "updatedAt": max(modified) if modified else "",
        "club": {"contact": contact, "history": history},
        "iceSchedule": ice_schedule,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default=os.environ.get("WORDPRESS_URL", DEFAULT_WORDPRESS_URL),
        help="Základná URL WordPressu (alebo WORDPRESS_URL).",
    )
    parser.add_argument("--limit", type=int, help="Importovať iba N najnovších článkov.")
    args = parser.parse_args()

    for directory in (IMAGE_ROOT, DOCUMENT_ROOT, IMAGE_MIRROR, DOCUMENT_MIRROR):
        if directory.exists():
            shutil.rmtree(directory)
    posts = import_posts(args.url, args.limit)
    if not posts:
        raise SystemExit("WordPress nevrátil žiadne publikované články")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({
            "schemaVersion": 2,
            "source": args.url.rstrip("/"),
            "updatedAt": max(post["modified"] for post in posts),
            "posts": posts,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    pages = import_pages(args.url)
    PAGES_OUTPUT.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"OK: {len(posts)} publikovaných WordPress článkov, "
        "Klub a Rozpis ľadu"
    )


if __name__ == "__main__":
    main()
