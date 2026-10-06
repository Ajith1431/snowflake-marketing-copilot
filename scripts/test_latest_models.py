import requests, json, base64, time, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from env_keys import get_secret
key = get_secret("GEMINI_API_KEY")

models_to_try = [
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-3-pro-image",
]
for model in models_to_try:
    print(f"\nTrying {model}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "Generate a professional marketing poster image for an athleisure line called UT-ActiveWear by Nike. Clean modern commercial advertising style, portrait orientation. Show a runner in sleek training wear."}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    r = requests.post(url, json=payload, timeout=180)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    b64 = part["inlineData"].get("data", "")
                    mime = part["inlineData"].get("mimeType", "")
                    print(f"IMAGE! mime={mime}, size={len(b64)} chars")
                    ext = "png" if "png" in mime else "jpg"
                    with open(f"output/creative/poster_{model.replace('-','_')}.{ext}", "wb") as f:
                        f.write(base64.b64decode(b64))
                    print(f"SAVED poster_{model.replace('-','_')}.{ext}!")
                if "text" in part:
                    print(f"Text: {part['text'][:100]}")
    else:
        err = r.json().get("error", {}).get("message", "")[:300]
        print(f"Error: {err}")
    time.sleep(3)
print("\nDone!")
