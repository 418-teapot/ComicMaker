# -*- coding: UTF-8 -*-

import os
import shutil
import uuid
import tomli
import re
from glob import glob
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

# generate pages html and toc.ncx
class HTMLMaker(object):
    def __init__(self, info: dict, width: int, height: int):
        self.title = info["title"]
        self.width = width
        self.height = height
        self.chapter: dict[str, str] = {}

    def rename(self, dir: str) -> None :
        cnt: int = 1
        dirs = os.listdir(dir)
        dirs.sort(key=lambda x:int(x.split('.')[0]))
        for img in dirs:
            assert img.endswith("jpg") or img.endswith("png")
            old_name: str = os.path.join(dir, img)

            # w, h = Image.open(old_name).size
            # assert w == self.width and h == self.height

            new_img: str = "{:0>3d}.{}".format(cnt, img[-3:])
            new_name: str = os.path.join(dir, new_img)
            os.rename(old_name, new_name)

            cnt += 1
        shutil.copytree(dir, os.path.join("./backup", dir))
        assert os.path.exists("./html/images")
        os.rename(dir, os.path.join("./html/images", dir))

    def generateChapter(self):
        assert os.path.exists("./html/images")
        for dir in os.listdir("./html/images"):
            if dir == "前言":
                self.chapter["preface"] = "前言"
                os.rename("./html/images/前言", "./html/images/preface")
            elif dir == "后记":
                self.chapter["postscript"] = "后记"
                os.rename("./html/images/后记", "./html/images/postscript")
            else:
                chapter_num = re.match("第\d+话", dir).group()
                assert chapter_num is not None
                num = re.search("\d+", chapter_num).group()
                assert num is not None
                # chapter_name = re.split("第\d+话", dir)[1]
                # assert chapter_name is not None
                self.chapter[str(int(num))] = dir
                os.rename(os.path.join("./html/images", dir), os.path.join("./html/images", num))

    def generateHTML(self, title: str, src: str):
        doc = Document()
        html = doc.createElement("html");

        head = doc.createElement("head")
        meta_node = doc.createElement("meta")
        meta_node.setAttribute("charset", "UTF-8")
        head .appendChild(meta_node)
        title_node = doc.createElement("title")
        title_node.appendChild(doc.createTextNode(title))
        head.appendChild(title_node)
        html.appendChild(head)

        body = doc.createElement("body")
        div = doc.createElement("div")
        img = doc.createElement("img")
        # img.setAttribute("style", "width:{}px;height:{}px;margin-left:0px;margin-top:0px;margin-right:0px;margin-bottom:0px;".format(self.width, self.height))
        title_path = os.path.join("images", title)
        img_path = os.path.join(title_path, src)
        img.setAttribute("src", img_path)
        div.appendChild(img)
        body.appendChild(div)
        html.appendChild(body)

        doc.appendChild(html)

        html_file = "{}-{}.html".format(title, src[:-4])
        with open(os.path.join("./html", html_file), 'w', encoding='utf-8') as f:
            f.write(f'<!DOCTYPE html>\n')
            for node in doc.childNodes:
                node.writexml(f, indent="", addindent="\t", newl="\n")


    def generatePages(self):
        assert os.path.exists("./html/images")
        for chapter in os.listdir("./html/images"):
            chapter_path = os.path.join("./html/images", chapter)
            if os.path.isdir(chapter_path):
                for page in os.listdir(chapter_path):
                    self.generateHTML(chapter, page)

    def generateMeta(self, doc, head, content: str, name: str):
        assert head is not None
        meta = doc.createElement("meta")
        meta.setAttribute("content", content)
        meta.setAttribute("name", name)
        head.appendChild(meta)

    def generateNavPoint(self, doc, nav_map, cnt: int, text: str, src: str):
        nav_point = doc.createElement("navPoint")
        nav_point.setAttribute("playOrder", str(cnt))
        nav_point.setAttribute("id", "toc-{}".format(cnt))

        nav_label = doc.createElement("navLabel")
        text_node = doc.createElement("text")
        text_node.appendChild(doc.createTextNode(text))
        nav_label.appendChild(text_node)
        nav_point.appendChild(nav_label)

        content = doc.createElement("content")
        content.setAttribute("src", src)
        nav_point.appendChild(content)

        nav_map.appendChild(nav_point)

    def generateNavPoints(self, doc, nav_map):
        cnt: int = 1
        bias = 0
        if "preface" in self.chapter.keys():
            self.generateNavPoint(doc, nav_map, cnt, "前言", "html/preface-001.html")
            bias = 1

        while str(cnt) in self.chapter.keys():
            self.generateNavPoint(doc, nav_map, cnt + bias, self.chapter[str(cnt)], "html/{}-001.html".format(cnt))
            cnt += 1

        if "postscript" in self.chapter.keys():
            self.generateNavPoint(doc, nav_map, cnt + bias, "后记", "html/postscript-001.html")

    def generateTOC(self):
        doc = Document()

        ncx = doc.createElement("ncx")
        ncx.setAttribute("version", "2005-1")
        ncx.setAttribute("xmlns", "http://www.daisy.org/z3986/2005/ncx/")
        ncx.setAttribute("xml:lang", "en-US")

        head = doc.createElement("head")
        self.generateMeta(doc, head, "", "dtb:uid")
        self.generateMeta(doc, head, "", "dtb:depth")
        self.generateMeta(doc, head, "0", "dtb:totalPageCount")
        self.generateMeta(doc, head, "0", "dtb:maxPageNumber")
        self.generateMeta(doc, head, "true", "generated")
        ncx.appendChild(head)

        doc_title = doc.createElement("docTitle")
        title_text = doc.createElement("text")
        title_text.appendChild(doc.createTextNode(self.title))
        doc_title.appendChild(title_text)
        ncx.appendChild(doc_title)

        nav_map = doc.createElement("navMap")
        self.generateNavPoints(doc, nav_map)
        ncx.appendChild(nav_map)

        doc.appendChild(ncx)

        with open("./toc.ncx", "w", encoding="utf-8") as f:
            f.write(f"<?xml version='1.0' encoding='UTF-8'?>\n")
            f.write(f"<!DOCTYPE ncx PUBLIC '-//NISO//DTD ncx 2005-1//EN' 'http://www.daisy.org/z3986/2005/ncx-2005-1.dtd'>\n")
            for node in doc.childNodes:
                node.writexml(f, indent="", addindent="\t", newl="\n")

    def tidy(self):
        assert not os.path.exists("./html/images")
        os.makedirs("./html/images")
        for item in os.listdir("./"):
            if os.path.isdir(item) and item != ".git" and item != "html" and item != "backup":
                self.rename(item)

    def generate(self) -> dict:
        self.tidy()
        self.generateChapter()
        self.generatePages()
        self.generateTOC()
        return self.chapter

def getCoverName() -> str:
    assert os.path.exists("./cover.jpg") or os.path.exists("./cover.png")
    if os.path.exists("./cover.jpg"):
        return "cover.jpg"
    else:
        return "cover.png"

def getImgWH() -> tuple[int, int]:
    w, h = Image.open(getCoverName()).size
    return (w, h)

if __name__ == "__main__":
    with open("./config.toml", 'rb') as config:
        info = tomli.load(config)
    assert info is not None
    w, h = getImgWH()
    chapter = HTMLMaker(info, w, h).generate()
    XMLMaker(info, chapter, w, h).generate()
    os.system("kindlegen -c2 -dont_append_source -verbose content.opf")
