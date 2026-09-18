import requests
key = "AQ.Ab8RN6K14KnzXpr6fA62CL2SsolDX05bG6e218sAS5Z4L4ShEg"
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
