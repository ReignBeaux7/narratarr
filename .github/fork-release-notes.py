"""Release notes for this fork: Narratarr's own notes for the version, plus what the fork adds.

Used by .github/workflows/sync-upstream.yml:  python3 .github/fork-release-notes.py v0.8.8
"""
import os
import pathlib
import re
import sys

version = sys.argv[1].lstrip("v")
repo = os.environ.get("GITHUB_REPOSITORY", "ReignBeaux7/narratarr")
log = pathlib.Path("CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(rf"^## {re.escape(version)}\b[^\n]*\n(.*?)(?=^## |\Z)", log, re.S | re.M)
upstream = m.group(1).strip() if m else f"See [CHANGELOG.md](https://github.com/{repo}/blob/main/CHANGELOG.md)."

print(f"""## What's new in Narratarr {version}

{upstream}

## What this fork adds

Everything above, plus:

- **No page flashing.** Background refreshes keep the cards and covers that didn't change, instead of redrawing the whole page.
- **Phone-friendly Library.** Phones get small cover images, and touch screens skip the heavy blur effects, so big libraries don't crash mobile Safari.
- **Smarter release picking.** Most seeders wins, preferred versions such as GraphicAudio come first, and every part of a multi-part release is grabbed (Settings → Search & sources → Release picking).
- **Covers for indexer results.** Prowlarr and Torznab search results show cover art.
- **Automatic updates.** New official Narratarr releases are merged in and built automatically.

Full history of the fork's changes: [FORK-CHANGELOG.md](https://github.com/{repo}/blob/main/FORK-CHANGELOG.md)

## Install or update

Docker image: `ghcr.io/{repo.lower()}:latest`
""")
