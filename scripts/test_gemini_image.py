import requests, json
key = "AQ.Ab8RN6K14KnzXpr6fA62CL2SsolDX05bG6e218sAS5Z4L4ShEg"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={key}"
payload = {
    "contents": [{"parts": [{"text": "Generate a professional marketing poster image for a fitness tracker product called FitTrack. Clean modern commercial advertising style. Portrait orientation."}]}],
    "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}
}
r = requests.post(url, json=payload, timeout=120)
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2)[:2000])
# Check for images
for cand in data.get("candidates", []):
    for part in cand.get("content", {}).get("parts", []):
        print(f"Part keys: {list(part.keys())}")
        if "inlineData" in part:
            print(f"IMAGE FOUND! mime: {part['inlineData'].get('mimeType')}, data length: {len(part['inlineData'].get('data',''))}")
        if "text" in part:
            print(f"TEXT: {part['text'][:200]}")
