# Fork changelog

Changes in this fork on top of [Narratarr](https://github.com/narratarr/narratarr). For Narratarr's
own release notes, see [CHANGELOG.md](CHANGELOG.md) (also in the app under Settings → Updates →
What's new).

The fork's changes live in their own files, so new Narratarr releases merge in without conflicts:
`narratarr/mobilefix.py`, `narratarr/thumbs.py`, `narratarr/static/mobile.css`,
`narratarr/static/smooth.js`, `.github/workflows/sync-upstream.yml`, two lines in the `Dockerfile`,
and their tests.

## Automatic updates

Every 6 hours the fork checks for a new official Narratarr release, merges it, and builds
`ghcr.io/reignbeaux7/narratarr:latest`. Each merge is listed here.

<!-- sync-upstream adds a line below for every release it merges -->
- 2026-11-02: merged Narratarr **v0.8.8** (tidy library)

## Fork changes

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

### 2026-11-02 (first version)
- Forked from Narratarr **0.8.7**. First phone fix: small covers on the Library page and lighter
  effects on touch screens.
