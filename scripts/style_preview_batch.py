"""Style Preview batch runner — renders ONE subject prompt through EVERY style
in the library (same seed, so the only variable is the style), building the
data the gallery/ front-end reads: images, thumbs, and manifest.json.

Idempotent: styles already in the manifest with an existing file are skipped,
so rerunning after any interruption is safe. Run with a python that has PIL
(ComfyUI's embedded python works). By Clio."""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comfy_gen import post_prompt, wait_for, collect_images, OUTDIR
from comfy_gen_krea2 import krea2_turbo_workflow, load_style_names
from PIL import Image


def safe_name(name):
    return "".join(c for c in name if c.isalnum() or c in " -_()").strip()


def main():
    ap = argparse.ArgumentParser(description="Render one subject through every library style")
    ap.add_argument("--prompt", required=True, help="subject prompt (keep it MEDIUM-SILENT: "
                    "no 'photo of'/'illustration of' — each style claims its own medium)")
    ap.add_argument("--seed", type=int, default=1997)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gallery"),
                    help="output root (default: the bundled gallery/ folder)")
    ap.add_argument("--styles", nargs="*", default=None, help="subset of style names (default: ALL)")
    args = ap.parse_args()

    styles = args.styles or load_style_names()
    out_root = os.path.abspath(args.out)
    img_dir = os.path.join(out_root, "krea2")
    thumb_dir = os.path.join(img_dir, "thumbs")
    os.makedirs(thumb_dir, exist_ok=True)
    manifest_path = os.path.join(out_root, "manifest.json")

    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"subject_prompt": args.prompt, "seed": args.seed,
                    "sections": {"krea2": {"title": "KREA 2 Turbo",
                                           "template": "Style: {name}: {style}. Subject: {prompt}", "images": []}}}

    done = {e["style"] for e in manifest["sections"]["krea2"]["images"]
            if os.path.exists(os.path.join(out_root, e["file"]))}
    todo = [s for s in styles if s not in done]
    print(f"{len(styles)} requested, {len(styles) - len(todo)} already done, {len(todo)} to render")

    for i, style in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {style} ...", flush=True)
        graph = krea2_turbo_workflow(args.prompt, args.seed, style=style)
        entry = wait_for(post_prompt(graph)["prompt_id"], timeout=600)
        imgs = collect_images(entry)
        if not imgs:
            print(f"  !! no image returned for {style}, skipping")
            continue
        src = os.path.join(OUTDIR, imgs[0].get("subfolder", ""), imgs[0]["filename"])
        base = safe_name(style)
        dst = os.path.join(img_dir, base + ".png")
        shutil.copyfile(src, dst)
        im = Image.open(dst).convert("RGB")
        im.thumbnail((512, 512), Image.LANCZOS)
        im.save(os.path.join(thumb_dir, base + ".jpg"), quality=85)
        manifest["sections"]["krea2"]["images"].append({
            "style": style, "file": f"krea2/{base}.png",
            "thumb": f"krea2/thumbs/{base}.jpg", "seed": args.seed,
        })
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1, ensure_ascii=False)  # crash-safe: persist per style
        print(f"  -> {dst}")

    print(f"batch done — manifest has {len(manifest['sections']['krea2']['images'])} images")


if __name__ == "__main__":
    main()
