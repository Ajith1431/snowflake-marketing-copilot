import sys, os, json, base64
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.creative.creative_studio import generate_creative_assets, build_assets_zip

print("Generating creative assets for CareWell CW-FitTrack...")
assets = generate_creative_assets(
    client_name="CareWell",
    product_name="CW-FitTrack",
    campaign_objective="Brand Awareness",
    target_audience="Adults 25-45, health-conscious",
    brand_colours="#0068FF, #00D4AA, #FF6B35",
    tone_keywords="bold, modern, confident, approachable",
    creative_direction="Clean modern lifestyle visuals showing fitness tracking in everyday life",
    gemini_api_key="AQ.Ab8RN6K14KnzXpr6fA62CL2SsolDX05bG6e218sAS5Z4L4ShEg",
    event_name="Super Bowl 2025"
)

errors = assets.get("errors", {})
print(f"Errors: {errors}")
print(f"Demo mode: {assets.get('poster_demo_mode', True)}")
print(f"Posters generated: {len(assets.get('posters_b64', []))}")
print(f"Scenes: {len(assets.get('hero_scenes', []))}")

os.makedirs("output/creative", exist_ok=True)

for i, p in enumerate(assets.get("posters_b64", [])):
    if p:
        with open(f"output/creative/poster_{i+1}.png", "wb") as f:
            f.write(base64.b64decode(p))
        print(f"Saved output/creative/poster_{i+1}.png")

with open("output/creative/design_system.json", "w") as f:
    json.dump(assets.get("design_system", {}), f, indent=2)
print("Saved design_system.json")

with open("output/creative/video_storyboard.json", "w") as f:
    json.dump(assets.get("hero_scenes", []), f, indent=2)
print("Saved video_storyboard.json")

with open("output/creative/prompts.json", "w") as f:
    json.dump({
        "poster_prompt": assets.get("poster_prompt", ""),
        "video_prompt": assets.get("video_prompt", ""),
        "audio_script": assets.get("audio_script", {})
    }, f, indent=2)
print("Saved prompts.json")

with open("output/creative/creative_assets.zip", "wb") as f:
    f.write(build_assets_zip(assets))
print("Saved creative_assets.zip")
print("DONE!")
