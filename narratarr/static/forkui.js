// Release picking settings (part of the add-on fix, see narratarr/forkprefs.py).
// Adds a "Release picking" section under Settings → Search & sources, saved on its own
// (to /api/settings/fork) the moment something changes, separate from Narratarr's form.
(() => {
  const ID = "fork-prefs";
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const html = (s) => `
    <div class="ph"><h3>Release picking</h3><p class="desc">How Narratarr chooses between releases for your Wanted books, in automatic searches and when you press Search now.</p></div>
    <div class="body">
      <div class="set-row">
        <label class="switch"><input type="checkbox" data-fork="prefer_seeders" ${s.prefer_seeders ? "checked" : ""}><i></i><span><b>Most seeders wins</b><small>Among releases that clearly match the book, take the one with the most seeders. Off: Narratarr's usual order (exact title, free LibriVox, M4B, then seeders).</small></span></label>
      </div>
      <div class="set-row">
        <label for="fork-words"><b>Preferred versions</b><small>Releases with any of these words win whenever one matches, such as GraphicAudio. Separate words with commas; leave empty for none.</small></label>
        <input class="input" id="fork-words" data-fork="preferred_words" value="${esc(s.preferred_words)}" placeholder="GraphicAudio" style="max-width:280px" />
      </div>
      <div class="set-row">
        <label class="switch"><input type="checkbox" data-fork="all_parts" ${s.all_parts ? "checked" : ""}><i></i><span><b>Grab every part</b><small>When the release is one part of several ("Part 1 of 3"), grab the other parts too. Each part becomes its own book, like GraphicAudio publishes them.</small></span></label>
      </div>
      <p class="hint" data-fork-status aria-live="polite"></p>
    </div>`;

  async function call(method, body) {
    const r = await fetch("/api/settings/fork", {
      method, credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) throw new Error(r.status === 403 ? "Only an admin can change this." : `Couldn't save (${r.status}).`);
    return r.json();
  }

  async function mount(anchor) {
    if (document.getElementById(ID)) return;
    const panel = document.createElement("section");
    panel.className = "panel";
    panel.id = ID;
    panel.dataset.page = anchor.dataset.page;
    panel.hidden = anchor.hidden;
    anchor.after(panel);
    let s;
    try { s = await call("GET"); } catch { panel.remove(); return; } // not an admin, or not available
    panel.innerHTML = html(s);
    const status = panel.querySelector("[data-fork-status]");
    let timer;
    const save = async () => {
      const body = {};
      panel.querySelectorAll("[data-fork]").forEach((el) => { body[el.dataset.fork] = el.type === "checkbox" ? el.checked : el.value; });
      try { await call("PUT", body); status.textContent = "Saved."; } catch (e) { status.textContent = e.message; }
    };
    // Keep these out of Narratarr's own settings form (its unsaved-changes bar and Save button).
    for (const type of ["input", "change"]) {
      panel.addEventListener(type, (e) => {
        e.stopPropagation();
        if (!e.target.dataset.fork) return;
        clearTimeout(timer);
        timer = setTimeout(save, e.target.type === "checkbox" ? 0 : 600);
      });
    }
  }

  const look = () => {
    const anchor = [...document.querySelectorAll('#view section.panel[data-page="search"]')]
      .find((p) => /Wanted/.test(p.querySelector(".ph h3")?.textContent || ""));
    if (anchor) mount(anchor);
  };
  new MutationObserver(look).observe(document.documentElement, { childList: true, subtree: true });
  look();
})();
