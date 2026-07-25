"""KREA 2 Turbo txt2img, headless, with style-library support. By Clio.
Core recipe from ComfyUI's official KREA 2 template (krea2 TE type, euler/simple,
8 steps, cfg 1). LoRA is OPT-IN via --lora. --style pulls from the 397-entry
style library through the ClioStyle node (which must be installed = this repo
cloned into custom_nodes and ComfyUI restarted)."""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comfy_gen import post_prompt, wait_for, collect_images, OUTDIR

STYLES_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "styles.json")


def load_style_names():
    with open(STYLES_JSON, "r", encoding="utf-8") as f:
        return [e["name"] for e in json.load(f)]


def krea2_turbo_workflow(positive, seed, w=1024, h=1024, steps=8, style=None,
                         lora=None, lora_strength=0.8,
                         unet="krea2_turbo_fp8_scaled.safetensors",
                         clip="qwen3vl_4b_fp8_scaled.safetensors",
                         vae="qwen_image_vae.safetensors", prefix="style_gen"):
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": clip, "type": "krea2"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["4", 0]}},
    }
    model_src = "1"
    if lora:
        graph["2"] = {"class_type": "LoraLoaderModelOnly",
                      "inputs": {"model": ["1", 0], "lora_name": lora, "strength_model": lora_strength}}
        model_src = "2"
    if style:
        graph["11"] = {"class_type": "ClioStyle",
                       "inputs": {"prompt": positive, "style": style,
                                  "template": "Style: {style}. Subject: {prompt}"}}
        text_src, prefix_src = ["11", 0], ["11", 2]
    else:
        text_src, prefix_src = positive, prefix
    graph["5"] = {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": text_src}}
    graph["8"] = {"class_type": "KSampler",
                  "inputs": {"model": [model_src, 0], "positive": ["5", 0], "negative": ["6", 0],
                             "latent_image": ["7", 0], "seed": seed, "steps": steps, "cfg": 1.0,
                             "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    graph["10"] = {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix_src}}
    return graph


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="KREA 2 Turbo headless gen with style library")
    ap.add_argument("--prompt", default="a corgi wearing a tiny crown, sitting on a velvet cushion "
                    "in a sunlit study, looking regal")
    ap.add_argument("--style", default=None, help="style name from the library (see --list-styles)")
    ap.add_argument("--list-styles", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--lora", default=None, help="optional LoRA filename (OFF unless given)")
    ap.add_argument("--lora-strength", type=float, default=0.8)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    args = ap.parse_args()

    if args.list_styles:
        for n in load_style_names():
            print(n)
        sys.exit(0)

    seed = args.seed if args.seed is not None else random.randrange(2**48)
    graph = krea2_turbo_workflow(args.prompt, seed, w=args.width, h=args.height,
                                 style=args.style, lora=args.lora, lora_strength=args.lora_strength)
    print(f"POSTing (style={args.style or 'none'}, lora={args.lora or 'OFF'}, seed={seed})...")
    res = post_prompt(graph)
    pid = res["prompt_id"]
    print("prompt_id:", pid)
    entry = wait_for(pid, timeout=600)
    imgs = collect_images(entry)
    for i in imgs:
        print("  ->", os.path.join(OUTDIR, i.get("subfolder", ""), i["filename"]))
