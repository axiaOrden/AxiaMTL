import argparse
import asyncio
import os
import tempfile
import chardet
import shutil
import re
from pentago import Pentago
from pentago.lang import *

LANG_MAP = {
    'ja': JAPANESE,
    'ko': KOREAN,
    'en': ENGLISH,
    'auto': AUTO,
}

def detect_encoding(filepath):
    with open(filepath, 'rb') as f:
        raw = f.read(4096)
        return chardet.detect(raw)['encoding']

def convert_to_utf8(input_path):
    encoding = detect_encoding(input_path)
    if encoding.lower() != 'utf-8':
        print(f"[!] Detected encoding: {encoding} → converting to UTF-8...")
        tmp_path = tempfile.mktemp()
        with open(input_path, 'r', encoding=encoding, errors='ignore') as src, \
             open(tmp_path, 'w', encoding='utf-8') as dst:
            shutil.copyfileobj(src, dst)
        return tmp_path
    return input_path

def get_lang_pair(lang_str):
    try:
        src_code, tgt_code = lang_str.split(":")
        return LANG_MAP[src_code], LANG_MAP[tgt_code], tgt_code
    except:
        raise ValueError("Invalid language pair. Use format like 'ja:en', 'ko:en'")

def is_meaningful(text):
    # Skip text with no Kanji, Kana, or Hangul (punctuation-only or broken quote)
    return re.search(r'[ぁ-んァ-ン一-龯가-힣]', text) is not None

def clean_paragraph(text):
    # Normalize standalone quotes or ellipses
    text = text.strip()
    text = re.sub(r'^[「『（〈《]*$', '', text)
    text = re.sub(r'^[.…。]+$', '', text)
    text = re.sub(r'^\W+$', '', text)
    return text.strip()

async def translate_file(input_path, output_path, src_lang, tgt_lang):
    translator = Pentago(src_lang, tgt_lang)

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    paragraphs = [clean_paragraph(p) for p in re.split(r"\n\s*\n", content)]
    paragraphs = [p for p in paragraphs if is_meaningful(p)]

    with open(output_path, "w", encoding="utf-8") as out:
        for i, paragraph in enumerate(paragraphs):
            attempt = 0
            success = False

            while attempt < 3 and not success:
                try:
                    result = await translator.translate(paragraph)
                    if not result or "translatedText" not in result:
                        raise ValueError("Empty or malformed result")

                    translated = result["translatedText"]
                    out.write(translated + "\n\n")
                    print(f"[{i+1}] ✅ {paragraph[:30]} → {translated[:30]}")
                    success = True

                except Exception as e:
                    attempt += 1
                    if attempt < 3:
                        print(f"[{i+1}] ⚠️ Retry {attempt}/3 for: {paragraph[:30]}...")
                        await asyncio.sleep(0.5)  # Small delay before retry
                    else:
                        out.write("[Translation failed]\n")
                        out.write(paragraph + "\n\n")
                        print(f"[{i+1}] ❌ Failed after 3 tries — [{paragraph[:30]}...] Error: {e}")

def get_text_files(directory):
    return [os.path.join(directory, f) for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".txt")]

def get_output_path(input_path, out_folder, tgt_suffix):
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(out_folder, f"{base_name}.{tgt_suffix}.txt")
    
def main():
    parser = argparse.ArgumentParser(description="Multi-language paragraph translation using PentaGo.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", help="Single input text file")
    input_group.add_argument("-d", "--dir", help="Input folder containing .txt files")
    parser.add_argument("-f", "--folder", required=True, help="Output folder")
    parser.add_argument("-lang", "--language", required=True, help="Format: ja:en / ko:en / ja:zh / etc")
    parser.add_argument("-utf", "--utf8", action="store_true")
    parser.add_argument("-epub", "--epub", action="store_true")
    args = parser.parse_args()

    src_lang, tgt_lang, tgt_suffix = get_lang_pair(args.language)
    os.makedirs(args.folder, exist_ok=True)

    if args.dir:
        input_files = get_text_files(args.dir)
        print(f"[+] Found {len(input_files)} files in '{args.dir}' to translate.")
        for file_path in input_files:
            input_file = convert_to_utf8(file_path) if args.utf8 else file_path
            output_path = get_output_path(file_path, args.folder, tgt_suffix)
            print(f"→ Translating {file_path} → {output_path}")
            asyncio.run(translate_file(input_file, output_path, src_lang, tgt_lang))

    elif args.input:
        input_path = convert_to_utf8(args.input) if args.utf8 else args.input
        output_path = get_output_path(args.input, args.folder, tgt_suffix)
        print(f"→ Translating {args.input} → {output_path}")
        asyncio.run(translate_file(input_path, output_path, src_lang, tgt_lang))

    else:
        print("[!] Please provide either --input or --dir")

if __name__ == "__main__":
    main()
