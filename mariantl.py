import os
import argparse
from transformers import MarianTokenizer, MarianMTModel, pipeline
from transformers import logging as hf_logging

hf_logging.set_verbosity_error()  # Suppress unnecessary warnings

MODEL_NAME = "Helsinki-NLP/opus-mt-ja-en"

def load_model():
    print(f"🔄 Loading model: {MODEL_NAME} ...")
    try:
        tokenizer = MarianTokenizer.from_pretrained(MODEL_NAME)
        model = MarianMTModel.from_pretrained(MODEL_NAME)
        translator = pipeline("translation", model=model, tokenizer=tokenizer)
        print("✅ Model loaded successfully.")
        return translator
    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        exit(1)

def read_file_with_encoding_fallback(file_path):
    encodings = ['utf-8', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return [line.strip() for line in f if line.strip()]
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Failed to decode file with UTF-8 or UTF-16.")

def translate_file(input_path, output_path, translator):
    print(f"📄 Reading input: {input_path}")
    lines = read_file_with_encoding_fallback(input_path)
    print(f"🧠 Translating {len(lines)} lines...")

    # Create output file immediately
    with open(output_path, "w", encoding="utf-8") as out_f:
        out_f.write("")  # Just create the file first

    for i, line in enumerate(lines, 1):
        try:
            result = translator(line, max_length=512)[0]["translation_text"]
        except Exception as e:
            result = f"[Error: {e}]"
        with open(output_path, "a", encoding="utf-8") as out_f:
            out_f.write(result + "\n")
        print(f"[{i}/{len(lines)}] ✓ {line[:20]} → {result[:20]}")

    print(f"✅ Translation saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Input .txt file")
    parser.add_argument("-o", "--output", required=True, help="Output .txt file")
    args = parser.parse_args()

    translator = load_model()
    translate_file(args.input, args.output, translator)
