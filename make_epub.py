import argparse
import os
import re
from ebooklib import epub

def get_text_files(directory):
    files = [
        f for f in os.listdir(directory)
        if f.lower().endswith('.txt') and os.path.isfile(os.path.join(directory, f))
    ]
    # Sort naturally: "2.txt" before "10.txt"
    return sorted(files, key=lambda x: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', x)])

def build_epub(input_dir, output_path, title, author, language='en'):
    book = epub.EpubBook()
    book.set_identifier('id_' + title.replace(" ", "_"))
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    chapters = []
    files = get_text_files(input_dir)

    for i, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)
        chapter_title = os.path.splitext(filename)[0]
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        c = epub.EpubHtml(title=chapter_title, file_name=f'chap_{i+1}.xhtml', lang=language)
        c.content = f"<h1>{chapter_title}</h1><p>{content.replace('\n', '<br/>')}</p>"

        book.add_item(c)
        chapters.append(c)

    book.toc = chapters
    book.spine = ['nav'] + chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book, {})
    print(f"✅ EPUB created: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Convert .txt files to EPUB with TOC.")
    parser.add_argument('-d', '--dir', required=True, help="Input folder with .txt files")
    parser.add_argument('-o', '--output', default='output.epub', help="Output EPUB file path")
    parser.add_argument('-t', '--title', default='My Book', help="Book title")
    parser.add_argument('-a', '--author', default='Anonymous', help="Book author")
    parser.add_argument('-l', '--lang', default='en', help="Language code (default: en)")

    args = parser.parse_args()
    build_epub(args.dir, args.output, args.title, args.author, args.lang)

if __name__ == '__main__':
    main()
