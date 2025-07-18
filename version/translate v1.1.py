import argparse
import asyncio
import os
import tempfile
import chardet
import shutil
import re

# External sentence splitters
import nltk
import tinysegmenter
import kss  # Optional: remove if you’re not testing Korean yet



from pentago import Pentago
from pentago.lang import *
from vllm_translator import VLLMTranslator


LANG_MAP = {
    'ja': JAPANESE,
    'ko': KOREAN,
    'en': ENGLISH,
    'auto': AUTO,
}

nltk.download('punkt', quiet=True)

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

def split_text_by_sentence(text, lang):
    text = text.strip()
    if lang == JAPANESE:
        try:
            import tinysegmenter
            seg = tinysegmenter.TinySegmenter()
            # Split by 。 and keep it with the sentence
            chunks = []
            for sentence in text.split("。"):
                sentence = sentence.strip()
                if sentence:
                    chunks.append(sentence + "。")
            return chunks
        except Exception as e:
            print(f"[!] Failed to segment JP: {e}")
            return [text]
    elif lang == KOREAN:
        try:
            import kss
            return kss.split_sentences(text)
        except Exception as e:
            print(f"[!] Failed to segment KO: {e}")
            return [text]
    elif lang == ENGLISH:
        try:
            import nltk
            from nltk.tokenize import sent_tokenize
            return sent_tokenize(text)
        except Exception as e:
            print(f"[!] Failed to segment EN: {e}")
            return [text]
    else:
        return [text]


async def translate_file(input_path, output_path, src_lang, tgt_lang, original_name=None, return_translated_title=False, model="pentago"):
    if model == "vllm":
        translator = VLLMTranslator()
    else:
        translator = Pentago(src_lang, tgt_lang)
    stem = os.path.splitext(original_name or os.path.basename(input_path))[0]
    title_part = "-".join(stem.split("-")[1:]) if "-" in stem else stem

    # Try translating the title first
    try:
        if not title_part.strip():
            raise ValueError("Empty title_part")
        title_text = translator.translate(title_part)
        translated_title = title_text if isinstance(title_text, str) else title_text.get("translatedText", "")

        if not translated_title.strip():
            raise ValueError("Empty translation")
        print(f"📘 Title translated: {title_part} → {translated_title}")
    except Exception as e:
        translated_title = title_part or "Untitled"
        print(f"📘 Title fallback (error): {type(e).__name__}: {e} — for title: {title_part}")

    if return_translated_title:
        return translated_title

    # Read and segment original text
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    raw_paragraphs = re.split(r"\n\s*\n", content)

    # Save pre-split sentence version for preview
    prep_path = output_path.replace(".txt", ".pre.txt")
    with open(prep_path, "w", encoding="utf-8") as prep_file:
        for para in raw_paragraphs:
            cleaned = clean_paragraph(para)
            if is_meaningful(cleaned):
                split = split_text_by_sentence(cleaned, src_lang)
                for s in split:
                    prep_file.write(s.strip() + "\n")
    print(f"📄 Prepared split content saved to: {prep_path}")

    # Start translating full paragraphs
    print(f"✍️ Writing to final output file: {output_path}")
    with open(output_path, "w", encoding="utf-8") as out:
        for i, para in enumerate(raw_paragraphs):
            cleaned_para = clean_paragraph(para)
            if not is_meaningful(cleaned_para):
                continue

            # Optional: split into sentences internally, then merge again
            split_sentences = split_text_by_sentence(cleaned_para, src_lang)
            merged_para = " ".join(s.strip() for s in split_sentences if is_meaningful(s))

            attempt = 0
            success = False
            while attempt < 3 and not success:
                try:
                    result = translator.translate(merged_para)
                    translated = result if isinstance(result, str) else result.get("translatedText", "")

                    if not translated:
                        raise ValueError("Empty or malformed result")
                    out.write(translated.strip() + "\n\n")
                    print(f"[{i+1}] ✅ {cleaned_para[:30]} → {translated[:30]}")
                    success = True
                except Exception as e:
                    attempt += 1
                    if attempt < 3:
                        print(f"[{i+1}] ⚠️ Retry {attempt}/3 for: {cleaned_para[:30]}...")
                        await asyncio.sleep(0.5)
                    else:
                        out.write("[Translation failed]\n" + cleaned_para + "\n\n")
                        print(f"[{i+1}] ❌ Failed after 3 tries — [{cleaned_para[:30]}...] Error: {e}")


def get_text_files(directory):
    return sorted([
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(".txt")
    ])

def main():
    parser = argparse.ArgumentParser(description="Multi-language paragraph translation using PentaGo or vLLM.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input", help="Single input text file")
    input_group.add_argument("-d", "--dir", help="Input folder containing .txt files")
    parser.add_argument("-f", "--folder", required=True, help="Output folder")
    parser.add_argument("-lang", "--language", required=True, help="Format: ja:en / ko:en / ja:zh / etc")
    parser.add_argument("-utf", "--utf8", action="store_true")
    parser.add_argument("-epub", "--epub", action="store_true")
    parser.add_argument("--model", default="pentago", choices=["pentago", "vllm"],
                        help="Translation engine to use: pentago (default) or vllm (local)")

    args = parser.parse_args()
    src_lang, tgt_lang = get_lang_pair(args.language)
    os.makedirs(args.folder, exist_ok=True)

    if args.dir:
        input_files = get_text_files(args.dir)
        print(f"[+] Found {len(input_files)} files in '{args.dir}' to translate.")
        for file_path in input_files:
            input_file = convert_to_utf8(file_path) if args.utf8 else file_path

            # Step 1: Generate translated title in advance
            translated_title = asyncio.run(
                translate_file(input_file, None, src_lang, tgt_lang,
                               original_name=os.path.basename(file_path),
                               return_translated_title=True,
                               model=args.model)
            )

            stem = os.path.splitext(os.path.basename(file_path))[0]
            prefix = stem.split("-")[0] if "-" in stem else "0000"
            safe_title = sanitize_filename(translated_title)
            final_filename = f"{prefix}-{safe_title}.txt"
            final_path = os.path.join(args.folder, final_filename)

            # Step 2: Now actually translate into that final path
            asyncio.run(
                translate_file(input_file, final_path, src_lang, tgt_lang,
                               original_name=os.path.basename(file_path),
                               return_translated_title=False,
                               model=args.model)
            )

            print(f"✔️ Saved as: {final_filename}")

    elif args.input:
        input_path = convert_to_utf8(args.input) if args.utf8 else args.input

        translated_title = asyncio.run(
            translate_file(input_path, "TEMP.txt", src_lang, tgt_lang,
                           original_name=os.path.basename(input_path),
                           return_translated_title=True,
                           model=args.model)
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
