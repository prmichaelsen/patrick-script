#!/usr/bin/env python3
"""Deploy patrickscript.com/play via the patrickscript-play-landing CF Worker.

# @scry.entry
# id: code.patrickscript-play-deploy~b3d92ef6
# kind: code
# status: active
# weight: 0.85
# tags:
#   - "topic:patrickscript"
#   - "patrickscript"
#   - "topic:play"
#   - "play"
#   - "topic:deploy"
#   - "deploy"
#   - "topic:cloudflare-worker"
#   - "cloudflare-worker"
#   - "scope:patrick-script"
#   - "patrick-script"
# summary: >
#   Cloudflare Worker deploy script for patrickscript.com/play. Uploads
#   the rendered site/play.html as a Worker script named
#   patrickscript-play-landing and ensures the zone routes
#   patrickscript.com/play and patrickscript.com/play/* (plus the www.
#   variants) point at it. Co-exists with the existing
#   patrickscript-landing Worker (bound to patrickscript.com/*) — the
#   /play* routes are more specific and win at request time.
#   Routes:
#     patrickscript.com/play
#     patrickscript.com/play/*
#     www.patrickscript.com/play
#     www.patrickscript.com/play/*
#   Run from the patrick-script project root:
#     python site/deploy_play.py            # deploy
#     python site/deploy_play.py --dry-run  # show intent
#   Also: deploy_play.py, /play deploy, patrickscript-play-landing
#   worker, CF route hierarchy, /play* more specific than /*, zone
#   ed89a447e5a4316cdfd2b5cdcebe247d.
# rationale: >
#   The substrate's generalized agent.lib.deploy.deploy_landing_worker()
#   builds a single-route Worker that matches only / and /index.html.
#   /play is multi-path (/play, /play/<slug>), so this script ships its
#   own Worker template. Bypasses agent.lib.deploy intentionally; reuses
#   the secrets loader so creds stay in one place.
# applies: deploying patrickscript.com/play, rotating the play worker,
#   adding/removing /play routes
# seeded_questions:
#   - "How do I deploy patrickscript.com/play?"
#   - "Deploy patrickscript-play-landing worker"
#   - "patrickscript.com/play zone routes"
#   - "Cloudflare Worker /play deploy"
#   - "deploy_play.py uv run"
# @scry.entry.end

This script:

  1. Reads site/play.html (run site/build_play.py first to generate it).
  2. Wraps it in a small Worker script that serves the same HTML for any
     request whose pathname starts with /play (so /play and /play/<slug>
     deep-links both render the SPA — the page reads location.hash to
     select an example).
  3. PUTs to /workers/scripts/patrickscript-play-landing on the
     reflection account.
  4. Ensures four zone routes exist pointing at the new worker:
       patrickscript.com/play
       patrickscript.com/play/*
       www.patrickscript.com/play
       www.patrickscript.com/play/*

Zone id is hard-coded (looked up once via CF API). Update if the zone
changes.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REFLECTION = Path("/home/prmichaelsen/.acp/projects/reflection")
PATRICK = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REFLECTION))
from agent.lib.deploy import (  # noqa: E402
    CF_API_BASE,
    DeployError,
    _get_httpx,
    _load_secrets,
)


WORKER_NAME = "patrickscript-play-landing"
HTML_PATH = PATRICK / "site" / "play.html"
ZONE_ID = "ed89a447e5a4316cdfd2b5cdcebe247d"  # patrickscript.com
ROUTE_PATTERNS = [
    "patrickscript.com/play",
    "patrickscript.com/play/*",
    "www.patrickscript.com/play",
    "www.patrickscript.com/play/*",
]
SECRETS_PATH = REFLECTION / "agent/secrets/cloudflare.env"


def build_worker_script(html: str) -> str:
    """Wrap the /play HTML in a Worker that serves it for any /play* path."""
    # JS template literals can't contain unescaped backticks or ${ sequences.
    html_safe = (
        html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    )
    return (
        "addEventListener('fetch', event => {\n"
        "  event.respondWith(handleRequest(event.request))\n"
        "})\n\n"
        "const HTML = `"
        + html_safe
        + "`;\n\n"
        "async function handleRequest(request) {\n"
        "  const url = new URL(request.url)\n"
        "  const p = url.pathname\n"
        "  if (p === '/play' || p.startsWith('/play/')) {\n"
        "    return new Response(HTML, {\n"
        "      headers: {\n"
        "        'Content-Type': 'text/html; charset=utf-8',\n"
        "        'Cache-Control': 'public, max-age=300',\n"
        "      }\n"
        "    })\n"
        "  }\n"
        "  return new Response('Not Found', { status: 404 })\n"
        "}\n"
    )


def deploy(dry_run: bool = False) -> int:
    if not HTML_PATH.exists():
        print(
            f"error: {HTML_PATH} not found. Run "
            f"`uv run site/build_play.py` first.",
            file=sys.stderr,
        )
        return 2

    html = HTML_PATH.read_text(encoding="utf-8")
    script = build_worker_script(html)

    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"→ {prefix}Deploying /play via CF Worker: {WORKER_NAME}")
    print(f"  HTML: {len(html):,} bytes from site/play.html")
    print(f"  Worker script: {len(script):,} bytes")
    print(f"  Zone: {ZONE_ID[:8]}…  (patrickscript.com)")
    print(f"  Routes: {', '.join(ROUTE_PATTERNS)}")

    if dry_run:
        print("\n→ [DRY-RUN] Would PUT script and ensure routes.")
        return 0

    httpx = _get_httpx()
    secrets = _load_secrets(SECRETS_PATH)
    account_id = secrets["CLOUDFLARE_ACCOUNT_ID"]
    headers = {
        "X-Auth-Email": secrets["CLOUDFLARE_EMAIL"],
        "X-Auth-Key": secrets["CLOUDFLARE_API_KEY"],
    }

    with httpx.Client() as client:
        print(f"\n→ Uploading Worker script to {WORKER_NAME}…")
        resp = client.put(
            f"{CF_API_BASE}/accounts/{account_id}/workers/scripts/{WORKER_NAME}",
            headers={**headers, "Content-Type": "application/javascript"},
            content=script.encode("utf-8"),
            timeout=90.0,
        )
        if resp.status_code not in (200, 201):
            raise DeployError(
                f"Worker deploy failed (HTTP {resp.status_code}): "
                f"{resp.text[:500]}"
            )
        result = resp.json()
        if not result.get("success"):
            raise DeployError(f"Worker deploy API error: {result.get('errors')}")
        print(f"  ✓ Worker deployed: {result['result']['id']}")

        print(f"\n→ Checking zone routes…")
        resp = client.get(
            f"{CF_API_BASE}/zones/{ZONE_ID}/workers/routes",
            headers=headers,
            timeout=30.0,
        )
        if resp.status_code != 200:
            raise DeployError(
                f"Route list failed (HTTP {resp.status_code}): {resp.text[:300]}"
            )
        existing = {r.get("pattern"): r for r in resp.json().get("result", [])}

        for pattern in ROUTE_PATTERNS:
            existing_route = existing.get(pattern)
            if existing_route is not None:
                if existing_route.get("script") == WORKER_NAME:
                    print(
                        f"  ✓ Route already bound: {pattern} "
                        f"(id: {existing_route['id']})"
                    )
                    continue
                # Route exists but bound to a different worker — repoint it.
                print(
                    f"  → Re-binding route {pattern} from "
                    f"'{existing_route.get('script')}' to '{WORKER_NAME}'…"
                )
                resp = client.put(
                    f"{CF_API_BASE}/zones/{ZONE_ID}/workers/routes/"
                    f"{existing_route['id']}",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"pattern": pattern, "script": WORKER_NAME},
                    timeout=30.0,
                )
                if resp.status_code not in (200, 201):
                    raise DeployError(
                        f"Route re-bind failed (HTTP {resp.status_code}): "
                        f"{resp.text[:300]}"
                    )
                result = resp.json()
                if not result.get("success"):
                    raise DeployError(
                        f"Route re-bind API error: {result.get('errors')}"
                    )
                print(f"  ✓ Re-bound: {pattern}")
                continue
            resp = client.post(
                f"{CF_API_BASE}/zones/{ZONE_ID}/workers/routes",
                headers={**headers, "Content-Type": "application/json"},
                json={"pattern": pattern, "script": WORKER_NAME},
                timeout=30.0,
            )
            if resp.status_code not in (200, 201):
                raise DeployError(
                    f"Route creation failed (HTTP {resp.status_code}): "
                    f"{resp.text[:300]}"
                )
            result = resp.json()
            if not result.get("success"):
                raise DeployError(
                    f"Route creation API error: {result.get('errors')}"
                )
            print(
                f"  ✓ Route created: {pattern} (id: {result['result']['id']})"
            )

    print("\n✓ /play deployed")
    print("  https://patrickscript.com/play")
    print("  https://patrickscript.com/play#brainfuck")
    print("  https://patrickscript.com/play#fibonacci")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intent, make no CF API calls.",
    )
    args = parser.parse_args(argv)
    try:
        return deploy(dry_run=args.dry_run)
    except DeployError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
