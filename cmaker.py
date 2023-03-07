# -*- coding: UTF-8 -*-

import os
import uuid
import tomli
import re
from PIL import Image
from xml.dom.minidom import Document

# generate content.opf
class XMLMaker(object):
    def __init__(self, dict: dict[str, str], width: int, height: int):
        self.title = dict["title"]
        self.language = dict["language"]
        self.author = dict["author"]
        match dict["publisher"]:
            case "null":
                self.publisher = None
            case _:
                self.publisher = dict["publisher"]
        self.uuid = str(uuid.uuid4())
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
        self.generateMeta("{}x{}".format(self.width, self.height), "original-resolution")
        self.generateMeta("false", "region-mag")
        self.generateMeta("cover-image", "cover")

    def generateItem(self, href: str, id: str, media_type: str):
        item = self.doc.createElement("item")
        item.setAttribute("href", href)
        item.setAttribute("id", id)
        item.setAttribute("media_type", media_type)
        self.manifest.appendChild(item)
    
    def generateManifest(self):
        assert self.manifest is not None
        self.generateItem("toc.ncx", "ncx", "application/x-dtbncx+xml")
        self.generateItem(getCoverName(), "cover-image", "image/{}".format(getCoverName()[-3:]))
    
    def generateSpine(self):
        assert self.spine is not None
        self.spine.setAttribute("toc", "ncx")

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
        self.generateManifest()
        self.package.appendChild(self.manifest)

        self.spine = self.doc.createElement("spine")
        self.generateSpine()
        self.package.appendChild(self.spine)

        self.doc.appendChild(self.package)
        with open("./content.opf", 'w', encoding="utf-8") as f:
            self.doc.writexml(f, newl="\n", addindent="\t", encoding="utf-8")

# generate pages html and toc.ncx
class HTMLMaker(object):
    def __init__(self, width: int, height: int):
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

            w, h = Image.open(old_name).size
            assert w == self.width and h == self.height

            new_img: str = "{:0>3d}.{}".format(cnt, img[-3:])
            new_name: str = os.path.join(dir, new_img)
            os.rename(old_name, new_name)

            cnt += 1
        assert os.path.exists("./html/images")
        os.rename(dir, os.path.join("./html/images", dir))

    def generateChapter(self, dir):
        if dir == "前言":
            self.chapter[dir] = "preface"
        elif dir == "后记":
            self.chapter[dir] = "postsctipt"
        else:
            chapter_num = re.match("第\d+话", dir).group()
            assert chapter_num is not None
            num = re.search("\d+", chapter_num).group()
            assert num is not None
            # chapter_name = re.split("第\d+话", dir)[1]
            # assert chapter_name is not None
            self.chapter[dir] = num

    def generateHTML(self, title: str, src: str):
        doc = Document()
        html = doc.createElement("html");

        head = doc.createElement("head")
        title_node = doc.createElement("title")
        title_node.appendChild(doc.createTextNode(title))
        head.appendChild(title_node)
        html.appendChild(head)

        body = doc.createElement("body")
        div = doc.createElement("div")
        img = doc.createElement("img")
        img.setAttribute("style", "width:{}px;height:{}px;margin-left:0px;margin-top:0px;margin-right:0px;margin-bottom:0px;".format(self.width, self.height))
        title_path = os.path.join("images", title)
        img_path = os.path.join(title_path, src)
        img.setAttribute("src", img_path)
        div.appendChild(img)
        body.appendChild(div)
        html.appendChild(body)

        doc.appendChild(html)

        html_file = "{}-{}.html".format(self.chapter[title], src[:-4])
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

    def generateTOC(self):
        pass

    def tidy(self):
        assert not os.path.exists("./html/images")
        os.makedirs("./html/images")
        for item in os.listdir("./"):
            if os.path.isdir(item) and item != ".git" and item != "html":
                self.generateChapter(item)
                self.rename(item)

    def generate(self):
        self.tidy()
        self.generatePages()

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
    HTMLMaker(w, h).generate()
    XMLMaker(info, w, h).generate()
