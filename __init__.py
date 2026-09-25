"""💅 Clio Style Library — prompt style injector for KREA 2 / Qwen-encoder models.
Styles live in styles.json beside this file (style library by u/Dear-Spend-2865, 398 entries).
Edit styles.json + refresh the browser to pick up changes — no server restart needed
(INPUT_TYPES re-reads the file on every /object_info fetch).
"""
import json
import os
import re

_DIR = os.path.dirname(os.path.abspath(__file__))
_STYLES_PATH = os.path.join(_DIR, "styles.json")
_FAVORITES_PATH = os.path.join(_DIR, "favorites.json")
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


def _load_favorites():
    try:
        with open(_FAVORITES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_favorites(names):
    with open(_FAVORITES_PATH, "w", encoding="utf-8") as f:
        json.dump(names, f, ensure_ascii=False, indent=1)


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
    DESCRIPTION = "Injects a style paragraph from the 398-entry library into your prompt. " \
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


NODE_CLASS_MAPPINGS = {"ClioStyle": ClioStyle}
NODE_DISPLAY_NAME_MAPPINGS = {"ClioStyle": "💅 Clio Style Library"}
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

    # favorites persist server-side (favorites.json, gitignored) so they
    # survive restarts and are shared across every browser hitting this server
    @PromptServer.instance.routes.get("/clio_style/favorites")
    async def _clio_style_favorites_get(request):
        return _web.json_response(_load_favorites())

    @PromptServer.instance.routes.post("/clio_style/favorites")
    async def _clio_style_favorites_post(request):
        data = await request.json()
        style = data.get("style", "")
        favorite = bool(data.get("favorite"))
        names = _load_favorites()
        if favorite and style not in names:
            names.append(style)
        elif not favorite and style in names:
            names.remove(style)
        _save_favorites(names)
        return _web.json_response(names)

    # the whole web gallery, served by ComfyUI itself — the node preview links to it
    PromptServer.instance.routes.static("/clio_style/gallery", _GALLERY)
except Exception:
    # headless import (scripts, tests) — no server, no preview, node still works
    pass
