import deepl
import os
import argparse
from tqdm import tqdm

auth_key = os.getenv("DEEPL_API_KEY")  # Set this via export DEEPL_API_KEY=your-key
translator = deepl.Translator(auth_key)

def translate_with_deepl(paragraphs, source_lang="JA", target_lang="EN-US"):
    results = []
    for para in tqdm(paragraphs, desc="Translating with DeepL"):
        if not para.strip():
            results.append("")
            continue
        try:
            result = translator.translate_text(
                para,
                source_lang=source_lang,
                target_lang=target_lang
            )
            results.append(result.text)
        except Exception as e:
            results.append(f"[Translation Error] {str(e)}")
    return results

def main():py
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input file path")
    parser.add_argument("--lang", default="ja:en", help="Language pair like ja:en or ko:en")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    src, tgt = args.lang.lower().split(":")
    lang_map = {"ja": "JA", "en": "EN-US", "ko": "KO"}
    src_lang = lang_map.get(src, "JA")
    tgt_lang = lang_map.get(tgt, "EN-US")

    # Read input
    encodings = ['utf-8', 'utf-16']
    paragraphs = []
    for enc in encodings:
        try:
            with open(args.input, "r", encoding=enc) as f:
                paragraphs = [line.strip() for line in f if line.strip()]
            break
        except UnicodeDecodeError:
            continue

    translated = translate_with_deepl(paragraphs, src_lang, tgt_lang)
    out_file = args.output or f"{args.input}.{tgt}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        for line in translated:
            f.write(line + "\n")

    print(f"✅ Saved translated output to {out_file}")

if __name__ == "__main__":
    main()
