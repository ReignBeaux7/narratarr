# Fork changelog

Changes in this fork on top of [Narratarr](https://github.com/narratarr/narratarr). For easy-to-read
notes on each version (Narratarr's changes plus this fork's), see the
[Releases](https://github.com/ReignBeaux7/narratarr/releases) page. Narratarr's full history is in
[CHANGELOG.md](CHANGELOG.md) (also in the app under Settings → Updates → What's new).

The fork's changes live in their own files, so new Narratarr releases merge in without conflicts:
`narratarr/mobilefix.py`, `narratarr/forkprefs.py`, `narratarr/thumbs.py`,
`narratarr/static/mobile.css`, `narratarr/static/smooth.js`, `narratarr/static/forkui.js`,
`.github/workflows/sync-upstream.yml`, two lines in the `Dockerfile`, and their tests.

## Automatic updates

Every 6 hours the fork checks for a new official Narratarr release, merges it, and builds
`ghcr.io/reignbeaux7/narratarr:latest`. Each merge is listed here.

<!-- sync-upstream adds a line below for every release it merges -->
- 2026-11-12: merged Narratarr **v0.9.4** (also brings in 0.9.0–0.9.3; merged by hand, since 0.9.0 added a GitHub workflow the automatic sync isn't allowed to push)
- 2026-11-02: merged Narratarr **v0.8.8** (tidy library)

## Fork changes

### 2026-11-03
- **Release picking** (Settings → Search & sources → Release picking):
  - **Most seeders wins:** among releases that clearly match a Wanted book, the one with the most
    seeders is grabbed.
  - **Preferred versions:** releases with words you choose (GraphicAudio by default) win
    whenever one matches.
  - **Grab every part:** when a release is one part of several ("Part 1 of 3"), the other parts
    are grabbed too, each as its own book.
- **Covers for indexer results:** Prowlarr/Torznab search results now show cover art, looked up
  in Apple's audiobook catalog when the picture is shown.

### 2026-11-02
- **No more page flashing.** Narratarr re-reads the library every 2 seconds and used to redraw
  whole pages when anything changed, so pages flashed and covers faded in again. Now cards that
  didn't change stay as they are, and changed ones keep their loaded cover (`smooth.js`, every device).
- **Phone fix.** Phones get small cover thumbnails (about 480 px) instead of full-size art, and
  touch screens skip the heavy blur effects and entrance animations (`mobilefix.py`, `mobile.css`).
  Desktop looks the same as before. Cover files on disk are never changed.
- **Auto-sync** with official Narratarr releases (`sync-upstream.yml`).
- Reworked the earlier fix into add-on files and put Narratarr's own files back to the release
  versions, so syncs don't conflict.
- Fixed the sync's build step starting on the wrong repository.
- Each synced version now gets a **release** on GitHub with its notes, plus this changelog.

### 2026-11-02 (first version)
- Forked from Narratarr **0.8.7**. First phone fix: small covers on the Library page and lighter
  effects on touch screens.
