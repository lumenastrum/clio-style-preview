// 💅 Clio Style Library — live in-node preview + visual style picker.
// The node shows the selected style's gallery thumb; clicking it opens a
// searchable picker grid of every style's preview (thumbs served by the
// routes in __init__.py). Zero deps, zero image copies — the thumbs +
// manifest already ship with the node.
import { app } from "../../scripts/app.js";

const NONE = "✨ none";
const NONE_MSG = "✨ no style — prompt passes through untouched";
const GOLD = "#e8c47a";
const PINK = "#ffd9ec";

// ---------------------------------------------------------------------------
// visual picker (one shared modal for every ClioStyle node on the canvas)
// ---------------------------------------------------------------------------
let pickerSingleton = null;

async function getPicker() {
  if (pickerSingleton) return pickerSingleton;

  const [manifest, styles] = await Promise.all([
    fetch("/clio_style/gallery/manifest.json").then((r) => r.json()),
    fetch("/clio_style/styles.json").then((r) => r.json()).catch(() => []),
  ]);
  const sectionOf = {};
  const sectionOrder = [];
  for (const e of styles) {
    if (e.section && !sectionOrder.includes(e.section)) sectionOrder.push(e.section);
    if (e.section) sectionOf[e.name] = e.section;
  }
  const images = Object.values(manifest.sections || {}).flatMap((s) => s.images || []);

  const overlay = document.createElement("div");
  overlay.style.cssText =
    "position:fixed;inset:0;z-index:10000;display:none;align-items:center;justify-content:center;" +
    "background:rgba(10,6,9,.72);backdrop-filter:blur(3px);font-family:sans-serif;";

  const panel = document.createElement("div");
  panel.style.cssText =
    "width:min(1100px,92vw);height:min(82vh,880px);display:flex;flex-direction:column;" +
    "background:#181117;border:1px solid #7a3b5e;border-radius:14px;overflow:hidden;" +
    "box-shadow:0 24px 80px rgba(0,0,0,.6);";

  const header = document.createElement("div");
  header.style.cssText =
    "display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid #35222c;flex-wrap:wrap;";
  header.innerHTML =
    `<span style="color:${PINK};font-size:15px;font-weight:600;">💅 pick a style</span>` +
    `<input type="text" placeholder="search 397 styles…" style="flex:1;min-width:160px;background:#241722;` +
    `border:1px solid #46293a;border-radius:8px;color:#f4dce9;padding:6px 10px;font-size:13px;outline:none;">` +
    `<select style="background:#241722;border:1px solid #46293a;border-radius:8px;color:#f4dce9;padding:6px;font-size:13px;"></select>` +
    `<a href="/clio_style/gallery/index.html" target="_blank" style="color:${GOLD};font-size:12px;text-decoration:none;">open full gallery ↗</a>` +
    `<button style="background:none;border:none;color:#b48ea6;font-size:20px;cursor:pointer;line-height:1;">×</button>`;

  const grid = document.createElement("div");
  // fixed tracks + explicit image heights: aspect-ratio/minmax sizing cycles
  // collapse to 4px rows inside ComfyUI's global CSS (grid row ← tile ← img)
  grid.style.cssText =
    "flex:1;overflow-y:auto;display:grid;grid-template-columns:repeat(auto-fill,150px);" +
    "grid-auto-rows:max-content;justify-content:center;gap:10px;padding:14px;align-content:start;";

  panel.append(header, grid);
  overlay.append(panel);
  document.body.append(overlay);

  const search = header.querySelector("input");
  const tradSel = header.querySelector("select");
  const closeBtn = header.querySelector("button");
  tradSel.innerHTML =
    `<option value="">all traditions</option>` +
    sectionOrder.map((s) => `<option value="${s}">${s}</option>`).join("");

  let current = null; // {node, styleWidget}
  const tiles = images.map((entry) => {
    const tile = document.createElement("div");
    tile.style.cssText =
      "cursor:pointer;border:2px solid transparent;border-radius:10px;overflow:hidden;" +
      "background:#241722;transition:border-color .12s;";
    tile.dataset.style = entry.style;
    tile.dataset.section = sectionOf[entry.style] || "";
    const im = document.createElement("img");
    im.loading = "lazy";
    im.src = "/clio_style/thumb?style=" + encodeURIComponent(entry.style);
    im.draggable = false;
    im.style.cssText = "width:146px;height:146px;object-fit:cover;display:block;";
    const label = document.createElement("div");
    label.textContent = entry.style;
    label.style.cssText =
      "padding:5px 7px;font-size:11px;color:#e9cddc;line-height:1.3;display:-webkit-box;" +
      "-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.6em;";
    tile.append(im, label);
    tile.addEventListener("mouseenter", () => { if (tile.style.borderColor !== GOLD) tile.style.borderColor = "#7a3b5e"; });
    tile.addEventListener("mouseleave", () => { if (tile.dataset.style !== current?.styleWidget?.value) tile.style.borderColor = "transparent"; });
    tile.addEventListener("click", () => {
      if (!current) return;
      const { node, styleWidget } = current;
      styleWidget.value = entry.style;
      styleWidget.callback?.(entry.style, app.canvas, node);
      node.setDirtyCanvas(true, true);
      hide();
    });
    grid.append(tile);
    return tile;
  });

  function applyFilter() {
    const q = search.value.trim().toLowerCase();
    const t = tradSel.value;
    for (const tile of tiles) {
      const hit = (!q || tile.dataset.style.toLowerCase().includes(q)) && (!t || tile.dataset.section === t);
      tile.style.display = hit ? "" : "none";
    }
  }
  search.addEventListener("input", applyFilter);
  tradSel.addEventListener("change", applyFilter);

  function onKey(e) { if (e.key === "Escape") { e.stopPropagation(); hide(); } }
  function hide() {
    overlay.style.display = "none";
    document.removeEventListener("keydown", onKey, true);
    current = null;
  }
  function show(node, styleWidget) {
    current = { node, styleWidget };
    search.value = ""; tradSel.value = ""; applyFilter();
    let selected = null;
    for (const tile of tiles) {
      const isSel = tile.dataset.style === styleWidget.value;
      tile.style.borderColor = isSel ? GOLD : "transparent";
      if (isSel) selected = tile;
    }
    overlay.style.display = "flex";
    document.addEventListener("keydown", onKey, true);
    if (selected) selected.scrollIntoView({ block: "center" });
    else grid.scrollTop = 0;
    search.focus();
  }
  overlay.addEventListener("click", (e) => { if (e.target === overlay) hide(); });
  closeBtn.addEventListener("click", hide);

  pickerSingleton = { show };
  return pickerSingleton;
}

// ---------------------------------------------------------------------------
// the on-node preview widget
// ---------------------------------------------------------------------------
app.registerExtension({
  name: "clio.stylePreview",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== "ClioStyle") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);

      const wrap = document.createElement("div");
      wrap.style.cssText =
        "position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center;" +
        "background:#1a1418;border:1px solid #3a2a33;border-radius:8px;overflow:hidden;cursor:pointer;" +
        "font-family:sans-serif;user-select:none;";

      const img = document.createElement("img");
      // contain, not cover — the render is square and should never be cropped
      img.style.cssText = "width:100%;height:100%;object-fit:contain;display:none;";
      img.draggable = false;

      const empty = document.createElement("div");
      empty.style.cssText = "color:#b48ea6;font-size:12px;text-align:center;padding:10px;line-height:1.5;";
      empty.textContent = NONE_MSG;

      const caption = document.createElement("div");
      caption.style.cssText =
        "position:absolute;left:0;right:0;bottom:0;padding:4px 34px;font-size:11px;color:" + PINK + ";" +
        "background:linear-gradient(transparent,rgba(20,10,16,.85));text-shadow:0 1px 2px #000;" +
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-align:center;display:none;";

      wrap.append(img, empty, caption);
      wrap.addEventListener("click", async () => {
        const styleWidget = this.widgets?.find((w) => w.name === "style");
        if (!styleWidget) return;
        (await getPicker()).show(this, styleWidget);
      });

      const widget = this.addDOMWidget("style_preview", "clio_preview", wrap, { serialize: false });
      // fixed, width-independent height claim: the prompt textarea is the
      // node's flexible widget and absorbs any deficit — a greedy claim here
      // crushes it to zero on saved node sizes (object-fit keeps us honest)
      widget.computeSize = () => [0, 240];

      const styleWidget = this.widgets?.find((w) => w.name === "style");

      // the preview + picker replace the dropdown visually; the widget itself
      // stays (hidden) because it carries workflow serialization and the API
      // value — and if this extension ever fails to load, nothing hides it
      // and the dropdown simply comes back
      if (styleWidget) {
        styleWidget.hidden = true;
        styleWidget.computeSize = () => [0, -4];
      }

      const stepStyle = (dir) => {
        if (!styleWidget) return;
        let vals = styleWidget.options?.values;
        if (typeof vals === "function") vals = vals();
        if (!vals?.length) return;
        const idx = vals.indexOf(styleWidget.value);
        const next = vals[(idx + dir + vals.length) % vals.length];
        styleWidget.value = next;
        styleWidget.callback?.(next, app.canvas, this);
        this.setDirtyCanvas(true, true);
      };
      for (const dir of [-1, 1]) {
        const b = document.createElement("button");
        b.textContent = dir < 0 ? "‹" : "›";
        b.style.cssText =
          "position:absolute;top:50%;transform:translateY(-50%);" + (dir < 0 ? "left:6px;" : "right:6px;") +
          "width:26px;height:34px;border:none;border-radius:7px;background:rgba(20,10,16,.55);color:" + PINK + ";" +
          "font-size:18px;cursor:pointer;opacity:.65;transition:opacity .15s;line-height:1;padding:0;";
        b.addEventListener("mouseenter", () => (b.style.opacity = "1"));
        b.addEventListener("mouseleave", () => (b.style.opacity = ".65"));
        b.addEventListener("click", (e) => { e.stopPropagation(); stepStyle(dir); });
        wrap.append(b);
      }

      const update = () => {
        const style = styleWidget?.value;
        if (!style || style === NONE) {
          img.style.display = "none";
          caption.style.display = "none";
          empty.textContent = NONE_MSG;
          empty.style.display = "";
          wrap.title = "click to pick a style visually";
          return;
        }
        empty.style.display = "none";
        caption.style.display = "";
        caption.textContent = style;
        img.style.display = "";
        img.src = "/clio_style/thumb?style=" + encodeURIComponent(style);
        wrap.title = style + "\n\n(click to pick a style visually)";
        fetch("/clio_style/prose?style=" + encodeURIComponent(style))
          .then((res) => (res.ok ? res.json() : null))
          .then((d) => {
            // style may have changed while the fetch was in flight
            if (d?.prose && styleWidget?.value === style) {
              const prose = d.prose.length > 600 ? d.prose.slice(0, 600) + " …" : d.prose;
              wrap.title = style + "\n\n" + prose + "\n\n(click to pick a style visually)";
            }
          })
          .catch(() => {});
      };

      img.onerror = () => {
        img.style.display = "none";
        caption.style.display = "none";
        empty.textContent = "✦ no preview render for this style yet";
        empty.style.display = "";
      };

      if (styleWidget) {
        const cb = styleWidget.callback;
        styleWidget.callback = function () {
          const res = cb?.apply(this, arguments);
          update();
          return res;
        };
      }
      this._clioPreviewUpdate = update;
      update();

      requestAnimationFrame(() => {
        // +60 over the computed minimum: LiteGraph's minimum only budgets ~2
        // lines for the prompt textarea (the node's flexible widget)
        this.setSize([Math.max(this.size[0], 260), this.computeSize()[1] + 60]);
      });
      return r;
    };

    // workflow loads restore widget values without firing widget callbacks, and
    // restore a node height saved BEFORE the preview existed — refresh the
    // preview and grow the node so the prompt textarea isn't crushed
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function () {
      const r = onConfigure?.apply(this, arguments);
      setTimeout(() => {
        this._clioPreviewUpdate?.();
        const minH = this.computeSize()[1] + 60;
        if (this.size[0] < 260 || this.size[1] < minH) {
          this.setSize([Math.max(this.size[0], 260), Math.max(this.size[1], minH)]);
          this.setDirtyCanvas(true, true);
        }
      }, 0);
      return r;
    };
  },
});
