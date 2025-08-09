import argparse
import os
import re
import tomllib
from typing import Any

from ebooklib import epub

META_FILE: str = "meta.toml"
HTML_SUBPATH: str = "html"
IMAGE_SUBPATH: str = "images"
PRE_CHAPTER: str = "pre"
POST_CHAPTER: str = "post"
CHAPTER_MAP: dict[str, str] = {
    "前言": PRE_CHAPTER,
    "后记": POST_CHAPTER,
}
TITLE_MAP: dict[str, str] = {
    PRE_CHAPTER: "前言",
    POST_CHAPTER: "后记",
}


def get_meta_info(path: str) -> dict[str, Any]:
    file = os.path.join(path, META_FILE)
    data: dict[str, Any] = {}

    assert os.path.exists(file)
    with open(file, "rb") as f:
        data = tomllib.load(f)

    return data


def format_images(path: str) -> None:
    images_path: str = os.path.join(path, IMAGE_SUBPATH)
    if os.path.exists(images_path):
        return

    for dir in os.listdir(path):
        dir_path: str = os.path.join(path, dir)
        if not os.path.isdir(dir_path):
            continue

        if dir in CHAPTER_MAP:
            name: str = CHAPTER_MAP[dir]
        else:
            m = re.match(r"第(\d+)话", dir)
            if not m:
                print(f"Skipping {dir_path}, not a valid chapter directory.")
                continue
            name: str = m.group(1)

        new_path: str = os.path.join(path, IMAGE_SUBPATH, name)
        os.makedirs(new_path, exist_ok=True)
        try:
            os.rename(dir_path, new_path)
        except Exception as e:
            print(f"Error renaming {dir_path} to {new_path}: {e}")
            continue

        images: list[str] = os.listdir(new_path)
        images.sort(key=lambda x: int(re.match(r"(\d+)\.(\w+)", x).group(1)))

        for i, image in enumerate(images):
            image_path: str = os.path.join(new_path, image)
            _, ext = os.path.splitext(image)
            new_name: str = f"{i:03d}{ext}"
            try:
                os.rename(image_path, os.path.join(new_path, new_name))
            except Exception as e:
                print(f"Error renaming {image_path} to {new_name}: {e}")
                continue


def get_chapters(path: str) -> list[str]:
    chapters: list[str] = []

    if not os.path.exists(os.path.join(path, IMAGE_SUBPATH)):
        return chapters

    if os.path.exists(os.path.join(path, IMAGE_SUBPATH, PRE_CHAPTER)):
        chapters.append(PRE_CHAPTER)

    for chapter in os.listdir(os.path.join(path, IMAGE_SUBPATH)):
        if re.match(r"(\d+)", chapter):
            chapters.append(chapter)

    if os.path.exists(os.path.join(path, IMAGE_SUBPATH, POST_CHAPTER)):
        chapters.append(POST_CHAPTER)

    return chapters


def get_images(path: str, chapters: list[str]) -> dict[str, list[str]]:
    images: dict[str, list[str]] = {}

    for chapter in chapters:
        chapter_path: str = os.path.join(path, IMAGE_SUBPATH, chapter)
        if not os.path.exists(chapter_path):
            continue

        images[chapter] = []
        for image in os.listdir(chapter_path):
            if re.match(r"(\d+).(\w+)", image):
                images[chapter].append(image)

        images[chapter].sort(
            key=lambda x: int(re.match(r"(\d+).(\w+)", x).group(1))
        )

    return images


def make_book(
    path: str,
    output: str,
    meta: dict[str, Any],
    chapters: list[str],
    images: dict[str, list[str]],
) -> None:
    book: epub.EpubBook = epub.EpubBook()

    # Add meta data.
    if "title" in meta:
        book.set_title(meta["title"])
    if "author" in meta:
        book.add_author(meta["author"])
    if "language" in meta:
        book.set_language(meta["language"])
    else:
        book.set_language("zh")

    spine: list[Any] = []
    # Add cover image.
    cover: str = None
    for item in os.listdir(path):
        if re.match(r"cover\.(\w+)", item):
            cover = item

    if cover is not None:
        book.set_cover(cover, open(os.path.join(path, cover), "rb").read())
        spine.append("cover")

    spine.append("nav")

    toc: list[epub.EpubHtml] = []

    for chapter in chapters:
        for idx, image in enumerate(images[chapter]):
            base, ext = os.path.splitext(image)
            if chapter in TITLE_MAP:
                title: str = TITLE_MAP[chapter]
            else:
                title: str = f"第{chapter}话"
            page = epub.EpubHtml(
                title=title, file_name=f"{chapter}-{base}.xhtml", lang="zh"
            )
            page.content = f"""<html>
            <head></head>
            <body>
                <img src="static/images/{chapter}/{image}"/>
            </body>
            </html>
            """
            content: bytes = open(
                os.path.join(path, IMAGE_SUBPATH, chapter, image), "rb"
            ).read()
            img = epub.EpubImage(
                file_name=f"static/images/{chapter}/{image}",
                media_type=f"image/{ext[1:].lower()}",
                content=content,
            )
            book.add_item(page)
            book.add_item(img)
            spine.append(page)
            if idx == 0:
                toc.append(page)

    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.spine = spine
    epub.write_epub(output, book, {})


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i", "--input", type=str, default="./", help="Input files"
    )
    parser.add_argument(
        "-o", "--output", type=str, default="book.epub", help="Output file"
    )
    return parser


if __name__ == "__main__":
    parser: argparse.ArgumentParser = get_parser()
    args = parser.parse_args()
    path: str = args.input
    output: str = args.output

    info: dict[str, Any] = get_meta_info(path)
    format_images(path)
    chapters: list[str] = get_chapters(path)
    images: dict[str, list[str]] = get_images(path, chapters)
    make_book(path, output, info, chapters, images)
