import requests
import re


class VLLMTranslator():
    def __init__(self, endpoint="http://localhost:8000/v1/completions", model="TinyLlama/TinyLlama-1.1B-Chat-v1.0", max_tokens=512):
        self.endpoint = endpoint
        self.model = model
        self.max_tokens = max_tokens

    def translate(self, text, src_lang="ja", tgt_lang="en"):
        prompt = f"""You are a professional {src_lang.upper()}→{tgt_lang.upper()} translator.

    Translate the following {src_lang.upper()} text into natural, fluent {tgt_lang.upper()}.

    Respond only with:
    raw: [original]
    translation: [your result]

    ---

    raw: {text}
    translation:"""
        
        response = requests.post(
            self.endpoint,
            json={
                "model": self.model,
                "prompt": prompt,
                "max_tokens": self.max_tokens,
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            result_text = data["choices"][0]["text"]
            # Extract only the line after "translation:"
            match = re.search(r"translation:\s*(.+)", result_text, re.DOTALL)
            if match:
                return match.group(1).strip()
            return result_text.strip()
        else:
            raise RuntimeError(f"vLLM Translation Error: {response.status_code} - {response.text}")
