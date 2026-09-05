#!/usr/bin/env python3
"""Repository-local documentation gates. No product runtime or publication writes."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit

from cffconvert import Citation
from markdown_it import MarkdownIt
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parent.parent
REPO = "BradGroux/open-framework-commons"
URL = "https://github.com/" + REPO
LEGACY = {"1.0.0", "1.1.0"}
GITLEAKS = "8.30.1"
PARSER = MarkdownIt("commonmark").enable("table").enable("strikethrough")
PRODUCTS = ["AI-Native Operating Framework", "Influence Operating Framework", "AI Dev Days",
            "Relationship Operating Framework", "Focus Operating Framework"]
CANONICAL = ["README.md", "CHARTER.md", "BOUNDARIES.md", "CONTEXT.md", "GOVERNANCE.md"]


class Invalid(ValueError):
    pass


def command(args, root=ROOT):
    """Never treat a failed child process as an empty successful result."""
    try:
        result = subprocess.run(args, cwd=root, capture_output=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Invalid(f"Required command failed: {args[0]}") from exc
    if result.returncode:
        # Tool output can contain private content; name the operation, not its payload.
        raise Invalid(f"Command failed ({result.returncode}): {args[0]} {args[1] if len(args) > 1 else ''}")
    return result.stdout.decode("utf-8")


def inventory(root=ROOT, committed=False):
    args = ["git", "ls-tree", "-r", "--name-only", "-z", "HEAD"] if committed else ["git", "ls-files", "--cached", "-z"]
    return set(filter(None, command(args, root).split("\0")))


def version_date(version, historical=False):
    if historical and version in LEGACY:
        return None
    match = re.fullmatch(r"(\d{4})\.(\d{2})\.(\d{2})(?:\.([1-9]\d*))?", version)
    if not match:
        raise Invalid("Expected calendar version YYYY.MM.DD with optional positive revision suffix")
    try:
        return dt.date(*map(int, match.group(1, 2, 3)))
    except ValueError as exc:
        raise Invalid("Invalid calendar date in VERSION") from exc


def read_public(root, path, files):
    dest = root / path
    if path not in files or dest.is_symlink() or not dest.is_file():
        raise Invalid(f"Missing public regular file: {path}")
    if not dest.resolve().is_relative_to(root.resolve()):
        raise Invalid(f"Public file escapes repository: {path}")
    return dest.read_text(encoding="utf-8")


def metadata(root=ROOT, files=None):
    files = inventory(root) if files is None else files
    read = lambda p: read_public(root, p, files)
    version = read("VERSION").strip()
    day = version_date(version)
    for path in [*CANONICAL, "PRINCIPLES.md", "RESEARCH-AND-REVIEW.md", "LICENSE",
                 "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "project/RELEASING.md"]:
        read(path)
    status_section = read("README.md").split("## Status\n", 1)
    if len(status_section) != 2:
        raise Invalid("README needs its designated Status section")
    status = status_section[1].split("\n## ", 1)[0].strip()
    if (not status.startswith(f"Version {version} is the current edition.")
            or re.findall(r"^Version ([0-9.]+) is the current edition\.", status, re.M) != [version]):
        raise Invalid("README current edition mismatch")
    charter_status = re.findall(r"^- \*\*Status:\*\* (.+)$", read("CHARTER.md"), re.M)
    if charter_status != [f"Version {version} approved edition"]:
        raise Invalid("Charter current edition mismatch")
    entries = re.findall(r"^## \[([^]]+)\](.*)$", read("CHANGELOG.md"), re.M)
    if not entries or entries[0] != (version, " - " + str(day)) or sum(entry[0] == version for entry in entries) != 1:
        raise Invalid("First CHANGELOG entry/date mismatch")
    notes = read(f"project/releases/v{version}.md")
    if notes.splitlines()[0] != f"# Open Framework Commons v{version}":
        raise Invalid("Active release note heading mismatch")
    if f"**Release date:** {day}" not in notes:
        raise Invalid("Active release note date mismatch")
    for heading in ["## Compatibility", "## Adoption", "## Verification"]:
        if heading not in notes:
            raise Invalid("Active release notes need compatibility, adoption and verification sections")
    try:
        cff = read("CITATION.cff")
        Citation(cff).validate()  # Bundled CFF schema, not merely YAML loading.
        data = YAML(typ="safe").load(cff)
    except Exception as exc:
        raise Invalid("CITATION.cff schema validation failed") from exc
    if (str(data["version"]) != version or str(data["date-released"]) != str(day)
            or data.get("repository-code") != URL or data.get("url") != f"{URL}/releases/tag/v{version}"):
        raise Invalid("Citation edition/date/repository/release URL mismatch")
    for path in CANONICAL:
        text = read(path)
        if any(product not in text for product in PRODUCTS):
            raise Invalid(f"Incomplete five-product scope in {path}")
        if re.search(r"all four|exactly four|four ecosystem products|effects on all four|apply to all four", text):
            raise Invalid(f"Obsolete four-product scope in {path}")
    if "exactly five independent products" not in read("README.md"):
        raise Invalid("README scope count mismatch")
    return version


def inline_text(token):
    return "".join(t.content if t.type in {"text", "code_inline"} else
                   inline_text(t) if t.type == "image" else " " if t.type in {"softbreak", "hardbreak"} else ""
                   for t in (token.children or []))


def anchors(tokens):
    used = set()
    for index, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        text = inline_text(tokens[index + 1]).lower()
        # GitHub-style IDs for the supported heading vocabulary; retain hyphens/underscores.
        base = "".join(c for c in text if c in "-_ " or unicodedata.category(c)[0] in "LNM").replace(" ", "-")
        slug, count = base, 0
        while slug in used:
            count += 1
            slug = f"{base}-{count}"
        used.add(slug)
    return used


def markdown(root=ROOT, files=None):
    root = root.resolve()
    files = inventory(root) if files is None else files
    docs = {}
    for name in files:
        if not name.lower().endswith(".md"):
            continue
        text = read_public(root, name, files)
        docs[name] = PARSER.parse(text)
        lines = text.splitlines()
        for token in docs[name]:
            if token.type == "fence" and token.info.strip() == "mermaid":
                closing = lines[token.map[1] - 1].strip()
                if not re.fullmatch(re.escape(token.markup[0]) + "{" + str(len(token.markup)) + ",}", closing):
                    raise Invalid(f"{name}: unclosed Mermaid fence")
    ids = {name: anchors(tokens) for name, tokens in docs.items()}
    for name, tokens in docs.items():
        for token in tokens:
            for html in [token, *(token.children or [])]:
                if html.type in {"html_inline", "html_block"} and re.search(
                    r"<[^>]+\b(?:href|src|srcset|data|action)\s*=", html.content, re.I
                ):
                    raise Invalid(f"{name}: raw HTML navigation is unsupported")
            # CommonMark resolves reference links and titles; code tokens are not links.
            for child in token.children or []:
                if child.type not in {"link_open", "image"}:
                    continue
                target = child.attrGet("href" if child.type == "link_open" else "src") or ""
                parsed = urlsplit(target)
                if parsed.scheme in {"http", "https", "mailto"}:
                    continue
                if parsed.scheme or parsed.netloc or re.search(r"%(?![0-9a-fA-F]{2})", target):
                    raise Invalid(f"{name}: unsupported or malformed link")
                decoded = unquote(parsed.path, errors="strict")
                if decoded.startswith(("/", "\\")) or "\\" in decoded or "\0" in decoded:
                    raise Invalid(f"{name}: local link must stay in public inventory")
                dest = root / name if not decoded else root / Path(name).parent / decoded
                normalized = Path(os.path.normpath(dest))
                if not normalized.is_relative_to(root) or dest.is_symlink() or not dest.resolve().is_relative_to(root):
                    raise Invalid(f"{name}: local link escapes public inventory")
                relative = normalized.relative_to(root).as_posix()
                if relative not in files or not normalized.is_file():
                    raise Invalid(f"{name}: missing public link target")
                if parsed.fragment and relative in ids and unquote(parsed.fragment) not in ids[relative]:
                    raise Invalid(f"{name}: missing heading anchor")
    return docs


def hygiene(root=ROOT, files=None):
    files = inventory(root) if files is None else files
    policy = json.loads(read_public(root, "scripts/publication-policy.json", files))
    patterns = [re.compile(p, re.I) for p in policy["patterns"]]
    # Exact path + line digest exceptions cover only regex definitions, never directories.
    exceptions = {(e["path"], e["sha256"]) for e in policy["exceptions"]}
    for name in sorted(files):
        if (root / name).is_symlink():
            raise Invalid(f"Public symlink is not supported: {name}")
        raw = (root / name).read_bytes()
        text = raw.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in patterns):
                digest = hashlib.sha256(line.encode()).hexdigest()
                if (name, digest) not in exceptions:
                    raise Invalid(f"Publication policy violation: {name}:{n} (match redacted)")


def secrets(root=ROOT, files=None):
    root = root.resolve()
    files = inventory(root) if files is None else files
    if command(["gitleaks", "version"], root).strip() != GITLEAKS:
        raise Invalid(f"Install Gitleaks {GITLEAKS}; see project/RELEASING.md")
    with tempfile.TemporaryDirectory(prefix="commons-public-") as tmp:
        snapshot = Path(tmp)
        for name in files:
            source = root / name
            if source.is_symlink() or not source.resolve().is_relative_to(root):
                raise Invalid("Public inventory contains an unsafe path")
            target = snapshot / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        # Scan every publishable file, including policy, fixtures and historical reviews.
        command(["gitleaks", "dir", str(snapshot), "--no-banner", "--redact", "--log-level", "error"], root)


def diagrams(root=ROOT):
    docs = markdown(root)
    executable = root / "node_modules/.bin/mmdc"
    if not executable.is_file():
        raise Invalid("Missing diagram compiler; run npm ci --ignore-scripts")
    out = root / ".validation-render"
    out.mkdir(exist_ok=True)
    config = {"args": ["--no-sandbox"]} if os.environ.get("CI") else {}
    if os.environ.get("CHROME_PATH"):
        config["executablePath"] = os.environ["CHROME_PATH"]
    elif sys.platform == "darwin":
        config["executablePath"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    (out / "puppeteer.json").write_text(json.dumps(config))
    count = 0
    for name, tokens in sorted(docs.items()):
        for token in tokens:
            if token.type == "fence" and token.info.strip() == "mermaid":
                count += 1
                src = out / f"diagram-{count}.mmd"
                src.write_text(token.content)
                command([str(executable), "-i", str(src), "-o", str(out / f"diagram-{count}.svg"),
                         "-p", str(out / "puppeteer.json"), "-b", "transparent"], root)
    if count != 3:
        raise Invalid(f"Expected three canonical diagrams, found {count}; review inventory intentionally")
    print(f"Compiled {count} Mermaid diagrams.")


def gh_json(args, root=ROOT):
    # Every API request fixes both host and repository; GH_REPO cannot redirect it.
    return json.loads(command(["gh", "api", "--hostname", "github.com", *args], root))


def verify_release_response(release, tag, body):
    day = version_date(tag[1:], historical=True)
    if day is not None:
        try:
            published_day = dt.datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")).astimezone(dt.timezone.utc).date()
        except (KeyError, ValueError, TypeError) as exc:
            raise Invalid("Published release has no valid UTC publication date") from exc
        if published_day != day:
            raise Invalid("Edition date differs from UTC publication date")
    if (release.get("tag_name") != tag or release.get("draft") is not False
            or release.get("prerelease") is not False or release.get("author", {}).get("login") != "BradGroux"):
        raise Invalid("Published release identity/state mismatch")
    if body is not None:
        normalize = lambda s: s.replace("\r\n", "\n").rstrip("\n")
        if normalize(release.get("body") or "") != normalize(body):
            raise Invalid("Published release body differs from committed notes")


def release(tag=None, root=ROOT):
    current = (root / "VERSION").read_text().strip()
    tag = tag or f"v{current}"
    if not tag.startswith("v"):
        raise Invalid("Expected a version tag")
    version_date(tag[1:], historical=True)
    local_object = command(["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{tag}}"], root).strip()
    commit = command(["git", "rev-parse", f"refs/tags/{tag}^{{commit}}"], root).strip()
    if command(["git", "status", "--porcelain"], root).strip():
        raise Invalid("Release verification needs a clean working tree")
    if tag == f"v{current}":
        if command(["git", "rev-parse", "HEAD"], root).strip() != commit:
            raise Invalid("Current release tag must peel to HEAD")
        check(root, committed=True)
    if gh_json(["user"], root).get("login") != "BradGroux":
        raise Invalid("Expected GitHub identity BradGroux")
    ref = gh_json([f"repos/{REPO}/git/ref/tags/{tag}"], root)["object"]
    if ref.get("type") != "tag" or ref.get("sha") != local_object:
        raise Invalid("Remote annotated tag differs from local tag")
    remote = gh_json([f"repos/{REPO}/git/tags/{local_object}"], root)["object"]
    if remote.get("type") != "commit" or remote.get("sha") != commit:
        raise Invalid("Remote peeled commit mismatch")
    paths = set(command(["git", "ls-tree", "-r", "--name-only", commit], root).splitlines())
    note_path = f"project/releases/{tag}.md"
    body = command(["git", "show", f"{commit}:{note_path}"], root) if note_path in paths else None
    if tag != "v1.0.0" and body is None:
        raise Invalid("Release commit has no matching release note")
    if "VERSION" in paths and command(["git", "show", f"{commit}:VERSION"], root).strip() != tag[1:]:
        raise Invalid("Release commit VERSION does not match tag")
    published = gh_json([f"repos/{REPO}/releases/tags/{tag}"], root)
    verify_release_response(published, tag, body)
    print(f"Verified {tag} at {commit} in {REPO}.")
    if body is None:
        print("Historical v1.0.0 has no committed release note: identity/state verified, body comparison unavailable.")


def check(root=ROOT, committed=False):
    files = inventory(root, committed)
    # New content must be staged; ignored local recovery files are never included.
    for name in files:
        read_public(root, name, files) if (root / name).suffix in {".md", ".py", ".sh"} else None
    version = metadata(root, files)
    markdown(root, files)
    hygiene(root, files)
    secrets(root, files)
    empty_tree = command(["git", "hash-object", "-t", "tree", "/dev/null"], root).strip()
    command(["git", "diff", "--check", empty_tree, "HEAD"], root)
    command(["git", "diff", "--check", "HEAD"], root)
    print(f"Repository validation passed for {version} ({len(files)} public files).")


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("mode", choices=["repository", "release", "diagrams"])
    cli.add_argument("tag", nargs="?")
    args = cli.parse_args()
    try:
        if args.mode == "release":
            release(args.tag)
        elif args.mode == "diagrams":
            diagrams()
        else:
            check()
    except (Invalid, UnicodeError, OSError, ValueError) as exc:
        # Controlled failures only; external scanner/CFF payloads are never echoed.
        print(f"Validation failed: {exc if isinstance(exc, Invalid) else type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
