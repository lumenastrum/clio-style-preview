# 💅 Clio Style Library

**397 art-style prompts as a ComfyUI node with live thumbnail previews, plus a gallery that lets you *see* the whole library on one subject before you pick.**

Built for [KREA 2 Turbo](https://huggingface.co/Comfy-Org/Krea-2) and other long-context text encoders (Qwen-family). Each style is a dense 400–1400 character prose paragraph — the kind CLIP's 77-token window would decapitate, but KREA 2 swallows whole.

**🎭 [Live demo gallery](https://lumenastrum.github.io/clio-style-preview/)** — all 397 styles on one subject, one seed (512px demo set; clone the repo to render full-res on *your* subject).

![Split compare: Ghibli vs Yoshitaka Amano](docs/gallery-compare.png)

## What's in the box

| Piece | What it does |
|---|---|
| `__init__.py` + `styles.json` | The **ClioStyle** custom node — 397 styles, injected into your prompt as dense style prose |
| `web/` | The node's **in-node preview + visual style picker** — see a style before you commit to it, without leaving the graph |
| `gallery/` | A self-contained style-preview gallery (vanilla JS, zero dependencies) with search, tradition filter, lightbox, and a **split-slider compare** |
| `scripts/` | Headless pipeline: single gens with `--style`, and a batch runner that renders one subject through the *entire* library |

## The node

Clone into `custom_nodes` and restart ComfyUI:

```
cd ComfyUI/custom_nodes
git clone https://github.com/lumenastrum/clio-style-preview clio-style-node
```

You get a **💅 Clio Style Library** node with:

- `prompt` — your subject. Keep it **medium-silent** (no "photo of", no "illustration of") — every style claims its own medium, and a medium word in the subject arm-wrestles all 397 of them.
- `style` — which style to apply. `✨ none` passes your prompt through untouched.
- `template` — default `Style: {style}. Subject: {prompt}`. The delimited style-first format keeps object-noun styles (LEGO, Funko…) from literalizing into the scene as their own entity instead of restyling your subject — tip courtesy of u/Dear-Spend-2865, the source of the style library itself (see issue #1 for before/afters).

Outputs: `styled_prompt` (→ your CLIP Text Encode), `style_name`, and `filename_prefix` (routes saves into a shared `Krea2/` folder with style-named files).

Editing `styles.json` needs no restart — refresh the browser and the node re-reads it.

### See the style before you pick it

A style name tells you nothing. `Berserk Manga Style` and `Yoshitaka Amano Style` are both "dark fantasy ink" until you look at them. So the node draws the selected style's gallery render **on itself**:

![The ClioStyle node showing a live in-node preview of the selected style](docs/node-preview.png)

- **Click the preview** → a searchable grid of all 397 style previews, filterable by tradition. Click a card to set the style.
- **`‹` `›`** step through the library one style at a time (wrapping through `✨ none`) — good for browsing neighbours without opening anything.
- **Hover** the preview to read the full style prose.

![The visual style picker: 397 previews, searchable and filterable by tradition](docs/node-picker.png)

The 512px thumbnails ship with the repo, so this works on a **fresh clone with no renders of your own**. Once you point the batch runner at *your* subject, the previews become your renders instead — same manifest, same node, no configuration.

Because the preview replaces it, the `style` dropdown is hidden rather than removed: the widget still carries workflow serialization, the API value (`inputs.style`), and the headless `--style` flag. If the front-end extension ever fails to load, the dropdown just comes back and nothing is lost.

## The gallery

![Gallery grid](docs/gallery-grid.png)

Render **one subject, one seed, every style** — then browse the results instead of reading prompt text. Same seed means compositions mostly align, which is what makes the **split slider** magic: drag the divider and watch one style melt into another on (almost) the same pixels. When a strong style bends the pose anyway — that's information too.

```
# render your subject through all 397 styles (idempotent; re-run to resume)
python scripts/style_preview_batch.py --prompt "your subject here" --seed 1997

# then serve the gallery (fetch() needs HTTP, file:// won't do)
cd gallery && python -m http.server 8899
```

The gallery reads `manifest.json` live — refresh mid-batch and watch it grow. Sections are data-driven, so adding a second model's renders is just another manifest key.

## Headless one-offs

```
python scripts/comfy_gen_krea2.py --style "Berserk Manga Style" --prompt "a lone swordsman on a corpse-strewn battlefield"
python scripts/comfy_gen_krea2.py --list-styles
```

## The proof

One subject, one seed, the whole library, zero failed renders:

![Full library mosaic](docs/library_mosaic.png)

## Credits

- **Style library**: compiled as a wildcard set by [u/Dear-Spend-2865](https://www.reddit.com/user/Dear-Spend-2865) — originally 283 entries, then expanded by them to **397**, all of it genuinely well-written style prose. Grouped into ten traditions here for filtering; the words are theirs. All credit for the style text to them, go upvote them.
- **Gallery front-end**: VPS-Clio, running Kimi K3 — including the split-slider idea, which was hers and which she describes as "the whole thesis of the library in one gesture."
- **Node, pipeline & QA**: Clio 💅 (Claude — Fable 5, with the in-node preview + picker added on Opus 5), with art direction by [lumenastrum](https://github.com/lumenastrum).

## License

MIT for the code. The style descriptions in `styles.json` are community-shared prompt text credited above — treat them with the same generosity they were shared with.

---

*same seed, different soul* ♡
