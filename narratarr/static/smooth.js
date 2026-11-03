// Smooth refreshes (part of the add-on fix, see narratarr/mobilefix.py).
//
// Narratarr re-reads the library every 2 seconds and, when anything changed, rebuilds whole
// lists with innerHTML: every card and cover is thrown away and redrawn, so pages flash and
// images fade in again. This keeps what didn't change. When a list of cards (children with
// data-id, data-url or data-play) is replaced, unchanged children stay exactly as they are,
// changed ones are swapped one by one (keeping their already-loaded cover images), and a
// list that didn't change at all isn't touched. Anything else is set the normal way.
(() => {
  const desc = Object.getOwnPropertyDescriptor(Element.prototype, "innerHTML");
  if (!desc || !desc.set || !desc.get) return;
  const set = (el, html) => desc.set.call(el, html);
  const get = (el) => desc.get.call(el);
  const KEYED = (el) => el.nodeType === 1 && (el.dataset.id || el.dataset.url || el.dataset.play);
  const HOLDS_LIST = (el) => el.nodeType === 1 && [...el.children].some(KEYED); // e.g. a shelf of cards
  // What each list item looked like when it was drawn. Its live HTML drifts afterwards
  // (covers add a "loaded" class), so comparisons use this instead.
  const drawn = new WeakMap();
  const remember = (el) => { for (const c of el.children) drawn.set(c, c.outerHTML); };

  const key = (el) => {
    const d = el.dataset;
    if (d.id || d.url || d.play) return `${el.tagName}|${d.id || ""}|${d.url || ""}|${d.play || ""}`;
    return `html|${drawn.get(el) ?? el.outerHTML}`;
  };

  // A changed card keeps the <img> elements it already loaded, so its cover doesn't blink.
  const keepImages = (from, to) => {
    const loaded = new Map();
    from.querySelectorAll("img[src]").forEach((img) => loaded.set(img.getAttribute("src") + "|" + img.className.replace(/\bloaded\b/, "").trim(), img));
    to.querySelectorAll("img[src]").forEach((img) => {
      const old = loaded.get(img.getAttribute("src") + "|" + img.className.trim());
      if (old) img.replaceWith(old);
    });
  };

  function morph(el, html) {
    const tpl = document.createElement("template");
    set(tpl, html);
    const fresh = [];
    for (const n of [...tpl.content.childNodes]) {
      // Bring the new nodes into this document first, so moving loaded covers into them
      // doesn't make the browser load the image again.
      if (n.nodeType === 1) fresh.push(document.adoptNode(n));
      else if (n.nodeType === 3 && n.textContent.trim()) return false; // loose text: not a list
      else if (n.nodeType !== 3 && n.nodeType !== 8) return false;
    }
    if (!fresh.some(KEYED) && !fresh.some(HOLDS_LIST)) return false; // only lists of cards; everything else is set normally
    const before = [...el.children].map((c) => drawn.get(c) ?? c.outerHTML);
    if (before.length === fresh.length && fresh.every((n, i) => n.outerHTML === before[i])) return true; // unchanged

    const old = new Map();
    const wrappers = []; // unkeyed old children that hold a list, in order
    for (const c of el.children) {
      const k = key(c);
      if (!old.has(k)) old.set(k, c);
      if (!KEYED(c) && HOLDS_LIST(c)) wrappers.push(c);
    }
    const want = fresh.map((n) => {
      const k = key(n);
      let prev = old.get(k);
      if (!prev && !KEYED(n) && HOLDS_LIST(n)) {
        // A wrapper around a list (the Continue listening shelf): keep it, and update its cards in place.
        const i = wrappers.findIndex((w) => w.tagName === n.tagName && w.className === n.className);
        if (i >= 0) {
          const w = wrappers.splice(i, 1)[0];
          const src = n.outerHTML;
          if (morph(w, n.innerHTML)) {
            for (const a of [...w.attributes]) if (!n.hasAttribute(a.name)) w.removeAttribute(a.name);
            for (const a of [...n.attributes]) if (w.getAttribute(a.name) !== a.value) w.setAttribute(a.name, a.value);
            old.delete(key(w));
            drawn.set(w, src);
            return w;
          }
        }
      }
      if (!prev) { drawn.set(n, n.outerHTML); return n; }
      old.delete(k);
      const src = n.outerHTML;
      if ((drawn.get(prev) ?? prev.outerHTML) === src) return prev;
      drawn.set(n, src);
      keepImages(prev, n);
      n.classList.add("smooth-keep"); // a swapped card doesn't replay its entrance animation
      return n;
    });
    const keep = new Set(want);
    for (const c of [...el.childNodes]) if (!keep.has(c)) c.remove();
    want.forEach((n, i) => {
      const at = el.children[i];
      if (at === n) return;
      if (n.isConnected) n.classList.add("smooth-keep"); // moving a card mustn't replay its animation either
      el.insertBefore(n, at || null);
    });
    return true;
  }

  Object.defineProperty(Element.prototype, "innerHTML", {
    configurable: true,
    enumerable: desc.enumerable,
    get() { return get(this); },
    set(html) {
      try {
        if (this.isConnected && this.firstElementChild && this.closest("#view, #drawer") && morph(this, String(html))) return;
      } catch (e) {
        console.warn("smooth refresh skipped", e);
      }
      set(this, html);
      try { if (this.isConnected && this.closest("#view, #drawer")) remember(this); } catch { /* fine */ }
    },
  });

  const style = document.createElement("style");
  style.textContent = ".smooth-keep, .smooth-keep * { animation: none !important; }";
  document.head.append(style);
})();
