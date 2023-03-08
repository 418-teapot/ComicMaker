# -*- coding: UTF-8 -*-

import os
import uuid
import tomli
import tomli_w
import re
from glob import glob
from functools import wraps
from PIL import Image
from xml.dom.minidom import Document

# generate content.opf
class XMLMaker(object):
    def __init__(self, info: dict[str, str], chapter: dict[str, str], width: int, height: int):
        self.title = info["title"]
        self.language = info["language"]
        self.author = info["author"]
        match info["publisher"]:
            case "null":
                self.publisher = None
            case _:
                self.publisher = info["publisher"]
        self.uuid = str(uuid.uuid4())
        self.chapter = chapter
        self.width = width
        self.height = height
        self.metadata = None

    def generateMeta(self, content: str, name: str) -> None:
        meta = self.doc.createElement("meta")
        meta.setAttribute("content", content)
        meta.setAttribute("name", name)
        assert self.metadata is not None
        self.metadata.appendChild(meta)

    def generateDC(self, name: str, content) -> None:
        attr = self.doc.createElement("dc:{}".format(name))
        if content is not None:
            attr.appendChild(self.doc.createTextNode(content))
        assert self.metadata is not None
        self.metadata.appendChild(attr)

    def generateMetadata(self):
        assert self.metadata is not None
        self.metadata.setAttribute("xmlns:opf", "http://www.idpf.org/2007/opf")
        self.metadata.setAttribute("xmlns:dc", "http://purl.org/dc/elements/1.1/")

        self.generateMeta("comic", "book-type")
        self.generateMeta("true", "zero-gutter")
        self.generateMeta("true", "zero-margin")
        self.generateMeta("true", "fixed-layout")

        self.generateDC("title", self.title)
        self.generateDC("language", self.language)
        self.generateDC("creator", self.author)
        self.generateDC("publisher", self.publisher)

        self.generateMeta("portrait", "orientation-lock")
        self.generateMeta("horizontal-rl", "primary-writting-mode")
        # self.generateMeta("{}x{}".format(self.width, self.height), "original-resolution")
        self.generateMeta("false", "region-mag")
        self.generateMeta("cover-image", "cover")

    def generateItem(self, href: str, id: str, media_type: str):
        item = self.doc.createElement("item")
        item.setAttribute("href", href)
        item.setAttribute("id", id)
        item.setAttribute("media_type", media_type)
        self.manifest.appendChild(item)

    def generateItemRef(self, idref: str):
        itemref = self.doc.createElement("itemref")
        itemref.setAttribute("idref", idref)
        itemref.setAttribute("linear", "yes")
        self.spine.appendChild(itemref)
    
    def generateManifestAndSpine(self):
        assert self.manifest is not None
        self.generateItem("toc.ncx", "ncx", "application/x-dtbncx+xml")
        self.generateItem(getCoverName(), "cover-image", "image/{}".format(getCoverName()[-3:]))
        assert self.spine is not None
        self.spine.setAttribute("toc", "ncx")
        if "preface" in self.chapter.keys():
            prefaces = glob("html/preface*.html")
            prefaces.sort(key=lambda x:int(x.split('-')[1].split('.')[0]))
            for preface in prefaces:
                self.generateItem(preface, "item-{}".format(preface[5:-5]), "application/xhtml+xmlapplication/xhtml+xml")
                self.generateItemRef("item-{}".format(preface[5:-5]))
        cnt: int = 1
        while str(cnt) in self.chapter.keys():
            chapter_cnt = glob("html/{}-*.html".format(str(cnt)))
            chapter_cnt.sort(key=lambda x:int(x.split('-')[1].split('.')[0]))
            for page in chapter_cnt:
                self.generateItem(page, "item-{}".format(page[5:-5]), "application/xhtml+xml")
                self.generateItemRef("item-{}".format(page[5:-5]))
            cnt += 1
        if "postscript" in self.chapter.keys():
            postscripts = glob("html/postscript*.html")
            postscripts.sort(key=lambda x:int(x.split('-')[1].split('.')[0]))
            for postscript in postscripts:
                self.generateItem(postscript, "item-{}".format(postscript[5:-5]), "application/xhtml+xmlapplication/xhtml+xml")
                self.generateItemRef("item-{}".format(postscript[5:-5]))

    def generate(self):
        self.doc = Document()

        self.package = self.doc.createElement("package")
        self.package.setAttribute("version", "2.0")
        self.package.setAttribute("xmlns", "http://www.idpf.org/2007/opf")
        self.package.setAttribute("unique-identifier", "{" + self.uuid + "}")

        self.metadata = self.doc.createElement("metadata")
        self.generateMetadata()
        self.package.appendChild(self.metadata)

        self.manifest = self.doc.createElement("manifest")
        self.spine = self.doc.createElement("spine")
        self.generateManifestAndSpine()
        self.package.appendChild(self.manifest)
        self.package.appendChild(self.spine)

        self.doc.appendChild(self.package)
        with open("./content.opf", 'w', encoding="utf-8") as f:
            self.doc.writexml(f, newl="\n", addindent="\t", encoding="utf-8")

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
            meta = generate_element(doc, head, "meta", attr = { "charset": "UTF-8" })
            title_node = generate_element(doc, head, "title", text = title)
            body = generate_element(doc, html, "body")
            div = generate_element(doc, body, "div")
            img = generate_element(doc, div, "img", attr = { "src" : "{}".format(get_img_name(key, i)) })

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
    assert os.path.exists("./info.toml")
    with open("./info.toml", 'rb') as f:
        infos = tomli.load(f)["info"]
    assert os.path.exists("./meta.toml")
    with open("./meta.toml", 'rb') as f:
        meta = tomli.load(f)

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

    with open("./toc.ncx", "w", encoding="utf-8") as f:
        f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n")
        f.write(f"<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>\n")
        for node in doc.childNodes:
            node.writexml(f, indent="", addindent="\t", newl="\n")

if __name__ == "__main__":
    assert os.path.exists("./meta.toml")
    with open("./meta.toml", 'rb') as f:
        meta = tomli.load(f)
    format_files()
    generate_htmls()
    generate_toc()
    # XMLMaker(info, chapter, w, h).generate()
    # os.system("kindlegen -c2 -dont_append_source -verbose content.opf")
