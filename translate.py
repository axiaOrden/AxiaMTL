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
        return LANG_MAP[src_code], LANG_MAP[tgt_code]
    except:
        raise ValueError("Invalid language pair. Use format like 'ja:en', 'ko:en'")

def is_meaningful(text):
    return re.search(r'[ぁ-んァ-ン一-龯가-힣]', text) is not None

def clean_paragraph(text):
    text = text.strip()
    text = re.sub(r'^[「『（〈《]*$', '', text)
    text = re.sub(r'^[.…。]+$', '', text)
    text = re.sub(r'^\W+$', '', text)
    return text.strip()

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

async def translate_file(input_path, output_path, src_lang, tgt_lang, original_name=None, return_translated_title=False):
    translator = Pentago(src_lang, tgt_lang)
    stem = os.path.splitext(original_name or os.path.basename(input_path))[0]
    title_part = "-".join(stem.split("-")[1:]) if "-" in stem else stem

    try:
        title_result = await translator.translate(title_part)
        translated_title = title_result["translatedText"]
        print(f"📘 Title translated: {title_part} → {translated_title}")
    except Exception as e:
        translated_title = title_part
        print(f"📘 Title fallback (error): {e}")

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
                    translated = result.get("translatedText", "")
                    if not translated:
                        raise ValueError("Empty or malformed result")
                    out.write(translated + "\n\n")
                    print(f"[{i+1}] ✅ {paragraph[:30]} → {translated[:30]}")
                    success = True
                except Exception as e:
                    attempt += 1
                    if attempt < 3:
                        print(f"[{i+1}] ⚠️ Retry {attempt}/3 for: {paragraph[:30]}...")
                        await asyncio.sleep(0.5)
                    else:
                        out.write("[Translation failed]\n" + paragraph + "\n\n")
                        print(f"[{i+1}] ❌ Failed after 3 tries — [{paragraph[:30]}...] Error: {e}")

    if return_translated_title:
        return translated_title


def get_text_files(directory):
    return sorted([
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".txt")
    ])

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

    src_lang, tgt_lang = get_lang_pair(args.language)
    os.makedirs(args.folder, exist_ok=True)

    if args.dir:
        input_files = get_text_files(args.dir)
        print(f"[+] Found {len(input_files)} files in '{args.dir}' to translate.")
        for file_path in input_files:
            input_file = convert_to_utf8(file_path) if args.utf8 else file_path

            translated_title = asyncio.run(
                translate_file(input_file, "TEMP.txt", src_lang, tgt_lang,
                               original_name=os.path.basename(file_path),
                               return_translated_title=True)
            )

            stem = os.path.splitext(os.path.basename(file_path))[0]
            prefix = stem.split("-")[0] if "-" in stem else "0000"

            safe_title = sanitize_filename(translated_title)
            final_filename = f"{prefix}-{safe_title}.txt"
            final_path = os.path.join(args.folder, final_filename)

            os.rename("TEMP.txt", final_path)
            print(f"✔️ Saved as: {final_filename}")

    elif args.input:
        input_path = convert_to_utf8(args.input) if args.utf8 else args.input
        translated_title = asyncio.run(
            translate_file(input_path, "TEMP.txt", src_lang, tgt_lang,
                           original_name=os.path.basename(input_path),
                           return_translated_title=True)
        )
        stem = os.path.splitext(os.path.basename(args.input))[0]
        prefix = stem.split("-")[0] if "-" in stem else "0000"

        safe_title = sanitize_filename(translated_title)
        final_filename = f"{prefix}-{safe_title}.txt"
        final_path = os.path.join(args.folder, final_filename)

        os.rename("TEMP.txt", final_path)
        print(f"✔️ Saved as: {final_filename}")

if __name__ == "__main__":
    main()
