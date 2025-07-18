import argparse
import asyncio
import os
import tempfile
import chardet
import shutil
import nagisa
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
    return re.search(r'[ぁ-んァ-ン一-龯가-힣a-zA-Z]', text) is not None

def clean_paragraph(text):
    text = text.strip()
    text = re.sub(r'^[「『（〈《]*$', '', text)
    text = re.sub(r'^[.…。]+$', '', text)
    text = re.sub(r'^\W+$', '', text)
    return text.strip()

def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '', name).strip()

def split_text_by_sentence(text, lang):
    text = text.strip()

    if lang == JAPANESE:
        try:
            import nagisa
            sentences = re.split(r'(?<=[。！？])\s*', text)
            return [s for s in sentences if s.strip()]
        except ImportError:
            print("[!] Falling back to .split('。') — Nagisa not available.")
            return [s + "。" for s in text.split("。") if s.strip()]

    elif lang == KOREAN:
        import kss
        return kss.split_sentences(text)

    elif lang == ENGLISH:
        return nltk.tokenize.sent_tokenize(text)

    else:
        return [text]

async def translate_file(input_path, output_path, src_lang, tgt_lang, original_name=None, return_translated_title=False):
    translator = Pentago(src_lang, tgt_lang)
    stem = os.path.splitext(original_name or os.path.basename(input_path))[0]
    title_part = "-".join(stem.split("-")[1:]) if "-" in stem else stem

    try:
        title_text = await translator.translate(title_part)
        translated_title = title_text if isinstance(title_text, str) else title_text.get("translatedText", "")
        if not translated_title.strip():
            raise ValueError("Empty title")
        print(f"📘 Title translated: {title_part} → {translated_title}")
    except Exception as e:
        translated_title = title_part or "Untitled"
        print(f"📘 Title fallback: {translated_title} ({e})")

    if return_translated_title:
        return translated_title

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    raw_paragraphs = re.split(r"\n\s*\n", content)

    prep_path = output_path.replace(".txt", ".pre.txt")
    with open(prep_path, "w", encoding="utf-8") as prep_file:
        for para in raw_paragraphs:
            cleaned = clean_paragraph(para)
            if is_meaningful(cleaned):
                for s in split_text_by_sentence(cleaned, src_lang):
                    prep_file.write(s.strip() + "\n")
    print(f"📄 Prepared: {prep_path}")

    print(f"✍️ Writing: {output_path}")
    with open(output_path, "w", encoding="utf-8") as out:
        for i, para in enumerate(raw_paragraphs):
            cleaned_para = clean_paragraph(para)
            if not is_meaningful(cleaned_para):
                continue

            split_sentences = split_text_by_sentence(cleaned_para, src_lang)
            merged_para = " ".join(s.strip() for s in split_sentences if is_meaningful(s))

            for attempt in range(3):
                try:
                    result = await translator.translate(merged_para)
                    translated = result if isinstance(result, str) else result.get("translatedText", "")
                    if not translated:
                        raise ValueError("Empty translation")
                    out.write(translated.strip() + "\n\n")
                    print(f"[{i+1}] ✅ {cleaned_para[:30]} → {translated[:30]}")
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f"[{i+1}] ⚠️ Retry {attempt+1}/3...")
                        await asyncio.sleep(0.5)
                    else:
                        out.write("[Translation failed]\n" + cleaned_para + "\n\n")
                        print(f"[{i+1}] ❌ Failed: {e}")

def get_text_files(directory):
    return sorted([
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".txt")
    ])

def main():
    parser = argparse.ArgumentParser(description="Translate paragraphs using Pentago.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", help="Single input text file")
    input_group.add_argument("-d", "--dir", help="Input folder of .txt files")
    parser.add_argument("-f", "--folder", required=True, help="Output folder")
    parser.add_argument("-lang", "--language", required=True, help="Format: ja:en / ko:en / etc")
    parser.add_argument("-utf", "--utf8", action="store_true")
    args = parser.parse_args()

    src_lang, tgt_lang = get_lang_pair(args.language)
    os.makedirs(args.folder, exist_ok=True)

    if args.dir:
        input_files = get_text_files(args.dir)
        print(f"[+] {len(input_files)} files in: {args.dir}")
        for file_path in input_files:
            input_file = convert_to_utf8(file_path) if args.utf8 else file_path
            title = asyncio.run(translate_file(input_file, None, src_lang, tgt_lang, original_name=os.path.basename(file_path), return_translated_title=True))
            stem = os.path.splitext(os.path.basename(file_path))[0]
            prefix = stem.split("-")[0] if "-" in stem else "0000"
            final_filename = f"{prefix}-{sanitize_filename(title)}.txt"
            final_path = os.path.join(args.folder, final_filename)
            asyncio.run(translate_file(input_file, final_path, src_lang, tgt_lang, os.path.basename(file_path), False))
            print(f"✔️ Saved: {final_filename}")
    else:
        input_path = convert_to_utf8(args.input) if args.utf8 else args.input
        title = asyncio.run(translate_file(input_path, "TEMP.txt", src_lang, tgt_lang, original_name=os.path.basename(input_path), return_translated_title=True))
        stem = os.path.splitext(os.path.basename(args.input))[0]
        prefix = stem.split("-")[0] if "-" in stem else "0000"
        final_filename = f"{prefix}-{sanitize_filename(title)}.txt"
        final_path = os.path.join(args.folder, final_filename)
        os.rename("TEMP.txt", final_path)
        print(f"✔️ Saved: {final_filename}")

if __name__ == "__main__":
    main()
