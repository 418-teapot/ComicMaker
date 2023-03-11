# -*- coding: UTF-8 -*-

import os
import uuid
import tomli
import tomli_w
import re
from PIL import Image
from xml.dom.minidom import Document


def get_cover_name() -> str:
    pattern = re.compile(r'cover\w*\.(jpg|png)')
    for item in os.listdir("./"):
        if pattern.search(item) is not None:
            return item
    assert False
    return ""

def format_files() -> None:
    if not os.path.exists("./html/images"):
        os.makedirs("./html/images")

    if os.path.exists("./info.toml"):
        with open("./info.toml", 'rb') as f:
            info = tomli.load(f)
    else:
        info = { "info": [] }

    for dir in os.listdir("./"):
        if os.path.isdir(dir) and dir != "html":
            info["info"].append(format_chapter(dir))

    with open("./info.toml", 'wb') as f:
        tomli_w.dump(info, f)

def format_chapter(dir: str) -> dict:
    info = {}
    name: str = ""
    if dir == "前言":
        name = "preface"
    elif dir == "后记":
        name = "postscript"
    else:
        chapter_num = re.match("第\d+话", dir).group()
        assert chapter_num is not None
        num = re.search("\d+", chapter_num).group()
        assert num is not None
        name = str(int(num))

    images = os.listdir(dir)
    pattern = re.compile(r'\d+\.(jpg|png)')
    images.sort(key = lambda x : int(pattern.search(x).group().split(".")[0]))
    cnt: int = 1
    for image in images:
        old_name = os.path.join(dir, image)
        new_name = os.path.join(dir, "{:0>3d}.{}".format(cnt, image[-3:]))
        w, h = Image.open(old_name).size
        assert w < h
        os.rename(old_name, new_name)
        cnt += 1
    os.rename(dir, os.path.join("./html/images", name))

    info[name] = { "title": dir, "pages": cnt - 1}
    return info

def generate_element(doc, father, name, attr={}, text=None):
    sub_elem = doc.createElement(name)
    for attr_name, attr_content in attr.items():
        sub_elem.setAttribute(attr_name, attr_content)
    if text is not None:
        sub_elem.appendChild(doc.createTextNode(text))
    father.appendChild(sub_elem)
    return sub_elem

def generate_htmls():
    def get_img_name(key: str, i: int) -> str:
        path = os.path.join("./html/images", key)
        for img in os.listdir(path):
            pattern_str = "{:0>3d}\\.(jpg|png)".format(i)
            pattern = re.compile(pattern_str)
            name = pattern.match(img)
            if name is None:
                continue
            assert name is not None
            return "images/{}/{}".format(key, name.group())
        assert False
        return ""

    def generate_html(info: dict[str, dict]) -> None:
        key: str = list(info.keys())[0]
        title: str = info[key]["title"]
        num: int = info[key]["pages"]

        for file in os.listdir("./html"):
            pattern_str = "{}-\\d+\\.html".format(key)
            pattern = re.compile(pattern_str)
            if pattern.match(file) is not None:
                return
        
        for i in range(1, num + 1):
            doc = Document()
            html = generate_element(doc, doc, "html")
            head = generate_element(doc, html, "head")
            generate_element(doc, head, "meta", attr = { "charset": "UTF-8" })
            generate_element(doc, head, "title", text = key)
            body = generate_element(doc, html, "body")
            div = generate_element(doc, body, "div")
            generate_element(doc, div, "img", attr = { "src" : "{}".format(get_img_name(key, i)) })

            html_file = os.path.join("./html", "{}-{:0>3d}.html".format(key, i))
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(f'<!DOCTYPE html>\n')
                for node in doc.childNodes:
                    node.writexml(f, indent="", addindent="\t", newl="\n")

    assert os.path.exists("./info.toml")
    with open("./info.toml", 'rb') as f:
        infos = tomli.load(f)["info"]
    for info in infos:
        generate_html(info)

def generate_toc():
    with open("./meta.toml", 'rb') as f:
        meta = tomli.load(f)
    with open("./info.toml", 'rb') as f:
        infos = tomli.load(f)["info"]

    doc = Document()
    ncx = generate_element(doc, doc, "ncx",
                           attr = {
                                "version": "2005-1",
                                "xmlns": "http://www.daisy.org/z3986/2005/ncx/",
                                "xml:lang": "en_US"
                           })
    head = generate_element(doc, ncx, "head")
    generate_element(doc, head, "meta", attr = { "content": "", "name": "dtb:uid" })
    generate_element(doc, head, "meta", attr = { "content": "", "name": "dtb:depth" })
    generate_element(doc, head, "meta", attr = { "content": "0", "name": "dtb:totalPageCount" })
    generate_element(doc, head, "meta", attr = { "content": "0", "name": "dtb:maxPageNumber" })
    generate_element(doc, head, "meta", attr = { "content": "true", "name": "generated" })
    doc_title = generate_element(doc, ncx, "docTitle")
    generate_element(doc, doc_title, "text", text = "{}".format(meta["title"]))
    nav_map = generate_element(doc, ncx, "navMap")

    info_dict = {}
    for info in infos:
        for k, v in info.items():
            info_dict[k] = v

    cnt: int = 1
    bias: int = 0
    if "preface" in info_dict.keys():
        nav_point = generate_element(doc, nav_map, "navPoint",
                                     attr = {
                                         "playOrder": "1",
                                         "id": "toc-1"
                                     })
        nav_label = generate_element(doc, nav_point, "navLabel")
        generate_element(doc, nav_label, "text", text = "{}".format(info_dict["preface"]["title"]))
        generate_element(doc, nav_point, "content", attr = { "src": "html/{}-001.html".format("preface") })
        bias = 1

    while str(cnt) in info_dict.keys():
        nav_point = generate_element(doc, nav_map, "navPoint",
                                     attr = {
                                         "playOrder": "{}".format(cnt + bias),
                                         "id": "toc-{}".format(cnt + bias)
                                     })
        nav_label = generate_element(doc, nav_point, "navLabel")
        generate_element(doc, nav_label, "text", text = "{}".format(info_dict[str(cnt)]["title"]))
        generate_element(doc, nav_point, "content", attr = { "src": "html/{}-001.html".format(str(cnt)) })
        cnt += 1

    if "postscript" in info_dict.keys():
        nav_point = generate_element(doc, nav_map, "navPoint",
                                     attr = {
                                         "playOrder": "{}".format(cnt),
                                         "id": "toc-{}".format(cnt)
                                     })
        nav_label = generate_element(doc, nav_point, "navLabel")
        generate_element(doc, nav_label, "text", text = "{}".format(info_dict["postscript"]["title"]))
        generate_element(doc, nav_point, "content", attr = { "src": "html/{}-001.html".format("postscript") })

    with open("./toc.ncx", 'w', encoding="utf-8") as f:
        f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n")
        f.write(f"<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>\n")
        for node in doc.childNodes:
            node.writexml(f, indent="", addindent="\t", newl="\n")

def generate_content():
    with open("./meta.toml", 'rb') as f:
        meta = tomli.load(f)
    with open("./info.toml", 'rb') as f:
        infos = tomli.load(f)["info"]

    doc = Document()
    package = generate_element(doc, doc, "package",
                               attr = {
                                    "version": "2.0",
                                    "xmlns": "http://www.idpf.org/2007/opf",
                                    "unique-identifier": str(uuid.uuid4())
                               })
    metadata = generate_element(doc, package, "metadata",
                                attr = {
                                    "xmlns:opf": "http://www.idpf.org/2007/opf",
                                    "xmlns:dc": "http://purl.org/dc/elements/1.1/"
                                })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "comic",
                         "name": "book-type"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "true",
                         "name": "zero-gutter"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "true",
                         "name": "zero-margin"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "true",
                         "name": "fixed-layout"
                     })

    generate_element(doc, metadata, "dc:title", text = "{}".format(meta["title"]))
    if "language" in meta.keys():
        language = meta["language"]
    else:
        language = "zh"
    generate_element(doc, metadata, "dc:language", text = "{}".format(language))
    generate_element(doc, metadata, "dc:creator", text = "{}".format(meta["author"]))
    if "publisher" in meta.keys():
        generate_element(doc, metadata, "dc:publisher", text = "{}".format(meta["publisher"]))
    else:
        generate_element(doc, metadata, "dc:publisher")

    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "portrait",
                         "name": "orientation-lock"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "horizontal-rl",
                         "name": "primary-writting-mode"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "false",
                         "name": "region-mag"
                     })
    generate_element(doc, metadata, "meta",
                     attr = {
                         "content": "cover-image",
                         "name": "cover"
                     })

    manifest = generate_element(doc, package, "manifest")
    spine = generate_element(doc, package, "spine", attr = { "toc": "ncx" })

    generate_element(doc, manifest, "item",
                     attr = {
                         "href": "toc.ncx",
                         "id": "ncx",
                         "media_type": "application/x-dtbncx+xml"
                     })
    generate_element(doc, manifest, "item",
                     attr = {
                         "href": "{}".format(get_cover_name()),
                         "id": "cover-image",
                         "media_type": "image/{}".format(get_cover_name()[-3:])
                     })

    info_dict = {}
    for info in infos:
        for k, v in info.items():
            info_dict[k] = v

    if "preface" in info_dict.keys():
        for i in range(1, info_dict["preface"]["pages"] + 1):
            generate_element(doc, manifest, "item",
                             attr = {
                                 "href": "html/{}-{:0>3d}.html".format("preface", i),
                                 "id": "item-{}-{:0>3d}".format("preface", i),
                                 "media_type": "application/xhtml+xml"
                             })
            generate_element(doc, spine, "itemref",
                             attr = {
                                 "idref": "item-{}-{:0>3d}".format("preface", i),
                                 "linear": "yes"
                             })

    cnt: int = 1
    while str(cnt) in info_dict.keys():
        for i in range(1, info_dict[str(cnt)]["pages"] + 1):
            generate_element(doc, manifest, "item",
                             attr = {
                                 "href": "html/{}-{:0>3d}.html".format(cnt, i),
                                 "id": "item-{}-{:0>3d}".format(cnt, i),
                                 "media_type": "application/xhtml+xml"
                             })
            generate_element(doc, spine, "itemref",
                             attr = {
                                 "idref": "item-{}-{:0>3d}".format(cnt, i),
                                 "linear": "yes"
                             })
        cnt += 1

    if "postscript" in info_dict.keys():
        for i in range(1, info_dict["postscript"]["pages"] + 1):
            generate_element(doc, manifest, "item",
                             attr = {
                                 "href": "html/{}-{:0>3d}.html".format("postscript", i),
                                 "id": "item-{}-{:0>3d}".format("postscript", i),
                                 "media_type": "application/xhtml+xml"
                             })
            generate_element(doc, spine, "itemref",
                             attr = {
                                 "idref": "item-{}-{:0>3d}".format("postscript", i),
                                 "linear": "yes"
                             })

    with open("./content.opf", 'w', encoding='utf-8') as f:
        doc.writexml(f, newl="\n", addindent="\t", encoding="utf-8")

if __name__ == "__main__":
    assert os.path.exists("./meta.toml")
    with open("./meta.toml", 'rb') as f:
        meta = tomli.load(f)
    format_files()
    generate_htmls()
    generate_toc()
    generate_content()
    os.system("kindlegen -c2 -dont_append_source -verbose content.opf")
