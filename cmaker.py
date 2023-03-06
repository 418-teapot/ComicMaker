import os
import uuid
import tomli
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

def getCoverName() -> str:
    assert os.path.exists("./cover.jpg") or os.path.exists("./cover.png")
    if os.path.exists("./cover.jpg"):
        return "cover.jpg"
    else:
        return "cover.png"

def getImgWH() -> tuple[int, int]:
    w, h = Image.open(getCoverName()).size
    return (w, h)

def rename(dir: str, width: int, height: int) -> None :
    cnt: int = 1
    for img in os.listdir(dir):
        assert img.endswith("jpg") or img.endswith("png")
        old_name: str = os.path.join(dir, img)

        w, h = Image.open(old_name).size
        assert w == width and h == height

        new_img: str = "{:0>3d}.{}".format(cnt, img[-3:])
        new_name: str = os.path.join(dir, new_img)
        os.rename(old_name, new_name)

if __name__ == "__main__":
    with open("./config.toml", 'rb') as config:
        info = tomli.load(config)
    assert info is not None
    w, h = getImgWH()
    XMLMaker(info, w, h).generate()