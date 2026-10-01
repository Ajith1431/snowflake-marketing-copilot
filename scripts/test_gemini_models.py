import requests, json, base64, time, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from env_keys import get_secret
key = get_secret("GEMINI_API_KEY")

# Try gemini-2.5-flash (text model that can also output images)
models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
for model in models_to_try:
    print(f"\nTrying {model}...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "Create a marketing poster image for a fitness tracker called FitTrack. Modern, clean, commercial style."}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
    }
    r = requests.post(url, json=payload, timeout=120)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "inlineData" in part:
                    b64 = part["inlineData"].get("data", "")
                    mime = part["inlineData"].get("mimeType", "")
                    print(f"IMAGE FOUND! mime={mime}, size={len(b64)} chars")
                    with open(f"output/creative/test_{model}.png", "wb") as f:
                        f.write(base64.b64decode(b64))
                    print(f"Saved test_{model}.png!")
                    break
                if "text" in part:
                    print(f"Text: {part['text'][:150]}")
    else:
        err = r.json().get("error", {}).get("message", "")[:200]
        print(f"Error: {err}")
    time.sleep(2)
