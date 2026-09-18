"""
creative_studio.py
NovaSpark Creative Studio — Gemini-powered
poster and video generation.
Standalone file — no Snowflake connection needed.
"""
from __future__ import annotations
import os, base64, json, io, zipfile, logging, requests
from typing import Optional
log = logging.getLogger(__name__)

def build_poster_prompt(client_name, product_name,
    campaign_objective, target_audience,
    brand_colours, tone_keywords,
    creative_direction, event_name=None):
    event_ctx = f"Event: {event_name}. " if event_name else ""
    return (
        f"Professional marketing poster for {client_name} "
        f"promoting {product_name}. "
        f"Objective: {campaign_objective}. "
        f"Audience: {target_audience}. "
        f"Brand colours: {brand_colours}. "
        f"Tone: {tone_keywords}. "
        f"Direction: {creative_direction}. {event_ctx}"
        f"Style: Clean modern commercial advertising. "
        f"Portrait orientation. No watermarks. No logos."
    )

def build_video_prompt(client_name, product_name,
    campaign_objective, creative_direction,
    event_name=None):
    event_ctx = f"Set during {event_name}. " if event_name else ""
    return (
        f"5-second cinematic brand video for "
        f"{product_name} by {client_name}. {event_ctx}"
        f"Goal: {campaign_objective}. "
        f"Visual: {creative_direction}. "
        f"Style: Premium brand film, smooth camera, "
        f"vibrant colours. No text. No logos."
    )

def generate_posters_gemini(prompt, api_key, count=3):
    if not api_key:
        return {"success": False, "demo_mode": True,
                "posters_b64": [],
                "error": "No API key provided"}
    try:
        posters = []
        for i in range(count):
            url = (
                "https://generativelanguage.googleapis.com"
                "/v1beta/models/gemini-2.5-flash-image"
                f":generateContent?key={api_key}"
            )
            payload = {
                "contents": [{
                    "parts": [{"text": f"Generate a marketing poster image (variation {i+1}): {prompt}"}]
                }],
                "generationConfig": {
                    "responseModalities": ["IMAGE", "TEXT"]
                }
            }
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            b64 = part["inlineData"].get("data", "")
                            if b64:
                                posters.append(b64)
        if posters:
            return {"success": True, "demo_mode": False,
                    "posters_b64": posters[:count],
                    "count": len(posters[:count]), "error": None}
        return {"success": False, "demo_mode": True,
                "posters_b64": [],
                "error": "No images returned from Gemini"}
    except Exception as exc:
        return {"success": False, "posters_b64": [],
                "error": str(exc)}

def _build_storyboard_scenes(prompt):
    return [
        {"scene": 1, "duration": "0-1s",
         "description": "Opening hero shot — product reveal",
         "camera": "Slow zoom in", "mood": "Anticipation"},
        {"scene": 2, "duration": "1-3s",
         "description": "Core benefit — audience connection",
         "camera": "Medium shot, subtle pan",
         "mood": "Emotional resonance"},
        {"scene": 3, "duration": "3-4s",
         "description": "Product in use — lifestyle context",
         "camera": "Close up detail", "mood": "Aspiration"},
        {"scene": 4, "duration": "4-5s",
         "description": "Brand end card — tagline",
         "camera": "Static brand frame", "mood": "Trust"},
    ]

def generate_video_gemini(prompt, api_key):
    return {
        "success": True, "demo_mode": True,
        "hero_frame_b64": None,
        "hero_scenes": _build_storyboard_scenes(prompt),
        "message": (
            "Video storyboard generated. "
            "Veo 2 access requires allowlist — "
            "showing scene breakdown instead."
        ),
        "error": None
    }

def build_design_system(client_name, brand_colours,
                         tone_keywords):
    colours = [c.strip() for c in brand_colours.split(",") if c.strip()]
    names = ["Primary","Secondary","Accent","Background","Text"]
    palette = [{"name": names[i] if i < len(names) else f"Colour {i+1}",
                "hex": c,
                "usage": f"{names[i]} elements"}
               for i, c in enumerate(colours[:5])]
    tones = [t.strip() for t in tone_keywords.split(",")]
    return {
        "client": client_name,
        "palette": palette,
        "tone": tones,
        "do": [
            "Use brand colours consistently",
            "Lead with benefits not features",
            "Show real people in real situations",
            "Use active voice"
        ],
        "dont": [
            "Use competitor names",
            "Make unsubstantiated claims",
            "Crowd the composition",
            "Use generic stock imagery"
        ]
    }

def generate_creative_assets(client_name, product_name,
    campaign_objective, target_audience,
    brand_colours, tone_keywords,
    creative_direction, gemini_api_key,
    event_name=None):
    errors = {}
    results = {}
    results["design_system"] = build_design_system(
        client_name, brand_colours, tone_keywords)
    poster_prompt = build_poster_prompt(
        client_name, product_name, campaign_objective,
        target_audience, brand_colours, tone_keywords,
        creative_direction, event_name)
    poster_result = generate_posters_gemini(
        poster_prompt, gemini_api_key, count=3)
    results["posters_b64"] = poster_result.get("posters_b64", [])
    results["poster_prompt"] = poster_prompt
    results["poster_demo_mode"] = poster_result.get("demo_mode", False)
    if poster_result.get("error"):
        errors["posters"] = poster_result["error"]
    video_prompt = build_video_prompt(
        client_name, product_name, campaign_objective,
        creative_direction, event_name)
    video_result = generate_video_gemini(
        video_prompt, gemini_api_key)
    results["hero_frame_b64"] = video_result.get("hero_frame_b64")
    results["hero_scenes"] = video_result.get("hero_scenes", [])
    results["video_prompt"] = video_prompt
    results["video_message"] = video_result.get("message", "")
    results["audio_script"] = {
        "prompt": (
            f"30-second script for {product_name} by {client_name}. "
            f"Tone: {tone_keywords}. Goal: {campaign_objective}. "
            f"Include: hook (5s), benefit (15s), "
            f"emotional close (7s), CTA (3s)."
        ),
        "duration": "30 seconds",
        "format": "Radio / Digital Audio"
    }
    results["campaign_meta"] = {
        "client": client_name, "product": product_name,
        "objective": campaign_objective,
        "audience": target_audience,
        "event": event_name or "N/A"
    }
    results["errors"] = errors
    return results

def build_assets_zip(assets):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, p in enumerate(assets.get("posters_b64",[])[:3]):
            if p:
                zf.writestr(f"poster_{i+1}.png",
                            base64.b64decode(p))
        ds = assets.get("design_system", {})
        if ds:
            zf.writestr("design_system.json",
                        json.dumps(ds, indent=2))
        zf.writestr("creative_prompts.json", json.dumps({
            "poster_prompt": assets.get("poster_prompt",""),
            "video_prompt": assets.get("video_prompt",""),
            "audio_script": assets.get(
                "audio_script",{}).get("prompt","")
        }, indent=2))
        scenes = assets.get("hero_scenes", [])
        if scenes:
            zf.writestr("video_storyboard.json",
                        json.dumps(scenes, indent=2))
    return buf.getvalue() or b"no-assets"
