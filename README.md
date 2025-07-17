# 📘 AxiaMTL — Machine Translation & EPUB Builder

A simple CLI-based workflow for translating `.txt` light novel files (Japanese/Korean/Chinese) into English (or other target languages) using [Pentago](https://github.com/Klypse/PentaGo), and compiling them into EPUB format with Table of Contents (TOC) support.

---

## 🔧 Requirements

### Python (Install via `pip`)
```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

### 🔤 Translate Text Files (`translate.py`)

Translate a single file or a folder of `.txt` files to your desired language using PentaGo.

#### 📄 Translate a single file:
```bash
python translate.py -i path/to/input.txt -f output_folder -lang ja:en
```

#### 📁 Translate all `.txt` files in a folder:
```bash
python translate.py -d input_folder -f output_folder -lang ja:en
```

#### 💡 Additional options:
- `-utf` — Automatically convert input files to UTF-8 before translation.
- `-epub` — Build an EPUB after translation using the result folder.

##### ✅ Example:
```bash
python translate.py -d novels/ -f translated/ -lang ja:en -utf -epub
```

---

### 📚 Build EPUB from Translated Files (`make_epub.py`)

Convert `.txt` files in a folder into a single EPUB file with proper title, author, language, and table of contents.

#### 🛠 Command:
```bash
python make_epub.py -d translated/ -o MyLightNovel.epub -t "Minogura" -a "Rinmi Akishima" -l en
```

#### 📌 Parameters:
- `-d` — Folder containing translated `.txt` files
- `-o` — Output EPUB filename (default: `output.epub`)
- `-t` — Title of the book
- `-a` — Author name
- `-l` — Language code (`en`, `ja`, `ko`, etc.)

---
