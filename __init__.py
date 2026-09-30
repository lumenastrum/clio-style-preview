"""💅 Clio Style Library — prompt style injector for KREA 2 / Qwen-encoder models.
Styles live in styles.json beside this file (414 entries: the style library by u/Dear-Spend-2865 plus our own additions).
Edit styles.json + refresh the browser to pick up changes — no server restart needed
(INPUT_TYPES re-reads the file on every /object_info fetch).
"""
import json
import os
import re

_DIR = os.path.dirname(os.path.abspath(__file__))
_STYLES_PATH = os.path.join(_DIR, "styles.json")
_NONE = "✨ none"


def _load_styles():
    try:
        with open(_STYLES_PATH, "r", encoding="utf-8") as f:
            return {e["name"]: e["prompt"] for e in json.load(f)}
    except Exception:
        return {}


def _display_name(style):
    # "Film Noir (2)" is a dedupe suffix for the dropdown, not part of the style's name
    return re.sub(r"\s*\(\d+\)$", "", style)


class ClioStyle:
    @classmethod
    def INPUT_TYPES(cls):
        # library order, not alphabetical — the paste groups styles by tradition
        names = [_NONE] + list(_load_styles().keys())
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "", "dynamicPrompts": False}),
                "style": (names, {"default": _NONE}),
                # Style-first delimited format keeps the style from literalizing into the
                # scene as its own entity (tip from u/Dear-Spend-2865, see repo issue #1).
                # {name} restores the style's name ahead of its prose, as the source list
                # wrote it — many proses never say it themselves (repo issue #5)
                "template": ("STRING", {"default": "Style: {name}: {style}. Subject: {prompt}"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("styled_prompt", "style_name", "filename_prefix")
    FUNCTION = "apply"
    CATEGORY = "Clio 💅"
    DESCRIPTION = "Injects a style paragraph from the 414-entry library into your prompt. " \
                  "Outputs the styled prompt, the bare style name, and a Krea2/<style> filename prefix."

    def apply(self, prompt, style, template):
        prompt = prompt.strip()
        text = _load_styles().get(style, "")
        if style == _NONE or not text:
            styled, name = prompt, "unstyled"
        elif not prompt:
            styled = f"{_display_name(style)}: {text}" if "{name}" in template else text
            name = style
        else:
            # fill the style slots before the prompt, so braces in a user's prompt stay literal
            styled = (template.replace("{name}", _display_name(style)).replace("{style}", text)
                      .replace("{prompt}", prompt).strip())
            name = style
        safe = "".join(c for c in name if c.isalnum() or c in " -_()").strip()
        return (styled, name, "Krea2/" + safe)


class ClioStyleEncode:
    """ClioStyle + CLIP Text Encode in one node, with a style STRENGTH slider.

    Prompt weights like (text:0.8) do nothing on KREA 2 in ComfyUI: its Qwen3-VL text encoder
    tokenizes with weights disabled, so the parens and number are read as literal text. Softer
    wording ("a light touch of ...") didn't weaken the styles either. What does work is
    blending conditioning: encode the styled prompt and your plain prompt, then average them
    (core ConditioningAverage). A/B on seed 1997 (Simpsons/Manga/Ghibli): 0.5 gives a genuine
    in-between style, 0.25 is mostly unstyled, 0.75 is mostly styled. This node runs the core
    nodes themselves, so it matches that hand-built graph exactly."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                **ClioStyle.INPUT_TYPES()["required"],
                "strength": ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05,
                    "tooltip": "1.0 = full style, 0 = your prompt unstyled. Not linear: around 0.5 "
                               "blends the two looks, 0.25 is mostly unstyled, 0.75 mostly styled.",
                }),
            }
        }

    RETURN_TYPES = ("CONDITIONING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("conditioning", "styled_prompt", "style_name", "filename_prefix")
    FUNCTION = "encode"
    CATEGORY = "Clio 💅"
    DESCRIPTION = "Clio Style Library + text encode, with a style strength slider (a conditioning " \
                  "blend between the styled prompt and your plain prompt; prompt weights don't work on KREA 2)."

    def encode(self, clip, prompt, style, template, strength):
        import nodes  # lazy, so scripts can import this file without a running ComfyUI

        styled, name, prefix = ClioStyle().apply(prompt, style, template)
        plain = prompt.strip()
        encode = nodes.CLIPTextEncode().encode
        if strength <= 0.0:
            cond = encode(clip, plain)[0]  # a clean unstyled encode, not a zero-padded blend
        else:
            cond = encode(clip, styled)[0]
            if strength < 1.0 and styled != plain:
                cond = nodes.ConditioningAverage().addWeighted(cond, encode(clip, plain)[0], strength)[0]
        return (cond, styled, name, prefix)


NODE_CLASS_MAPPINGS = {"ClioStyle": ClioStyle, "ClioStyleEncode": ClioStyleEncode}
NODE_DISPLAY_NAME_MAPPINGS = {"ClioStyle": "💅 Clio Style Library", "ClioStyleEncode": "💅 Clio Style Encode"}
WEB_DIRECTORY = "./web"


# ---- in-node preview plumbing -----------------------------------------------
# Serves the gallery's own thumbs + manifest through ComfyUI so the front-end
# extension (web/clio_preview.js) can draw a live style preview on the node.
# No image copies, no extra deps — the same files the web gallery already ships.
try:
    from server import PromptServer
    from aiohttp import web as _web

    _GALLERY = os.path.join(_DIR, "gallery")

    def _manifest_entry(style):
        try:
            with open(os.path.join(_GALLERY, "manifest.json"), "r", encoding="utf-8") as f:
                man = json.load(f)
        except Exception:
            return None
        for sec in (man.get("sections") or {}).values():
            for img in sec.get("images", []):
                if img.get("style") == style:
                    return img
        return None

    @PromptServer.instance.routes.get("/clio_style/thumb")
    async def _clio_style_thumb(request):
        # style names can contain characters filenames can't (colons) — resolve
        # through the manifest instead of guessing a filename
        entry = _manifest_entry(request.rel_url.query.get("style", ""))
        if not entry:
            return _web.Response(status=404)
        rel = entry.get("thumb") or entry.get("file") or ""
        path = os.path.normpath(os.path.join(_GALLERY, rel))
        if not path.startswith(os.path.normpath(_GALLERY) + os.sep) or not os.path.isfile(path):
            return _web.Response(status=404)
        return _web.FileResponse(path)

    @PromptServer.instance.routes.get("/clio_style/prose")
    async def _clio_style_prose(request):
        style = request.rel_url.query.get("style", "")
        return _web.json_response({"style": style, "prose": _load_styles().get(style, "")})

    # the gallery's repo-layout fallback fetch ("../styles.json") lands here
    @PromptServer.instance.routes.get("/clio_style/styles.json")
    async def _clio_style_styles(request):
        return _web.FileResponse(_STYLES_PATH)

    # the whole web gallery, served by ComfyUI itself — the node preview links to it
    PromptServer.instance.routes.static("/clio_style/gallery", _GALLERY)
except Exception:
    # headless import (scripts, tests) — no server, no preview, node still works
    pass
