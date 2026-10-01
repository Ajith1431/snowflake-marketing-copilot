import requests, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from env_keys import get_secret
key = get_secret("GEMINI_API_KEY")
r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
models = r.json().get("models", [])
for m in models:
    name = m.get("name", "")
    methods = m.get("supportedGenerationMethods", [])
    if "image" in name.lower() or "imagen" in name.lower():
        print(f"{name}: {methods}")
print("---")
for m in models:
    name = m.get("name", "")
    methods = m.get("supportedGenerationMethods", [])
    if "gemini-2" in name and "flash" in name:
        print(f"{name}: {methods}")
