#  Python based web scrapper
#  Written by Barracoder
#  November 2018

import hashlib
import re
import urllib.error
import urllib.parse
import urllib.request


# TODO Pagination detection and isolation -- special algorithm


class DeepRecurse:
    visited = set()
    matches = set()

    def __init__(self, web_content, parent=None, depth=1, **kwargs):
        self.max_depth = kwargs.get("max_depth", 10)
        self.depth = depth
        self.children = {}
        self.parent = parent
        self.web_content = web_content
        self.next = None
        self.__matches = set()
        if self.depth == 1:
            if not self.web_content.is_valid:
                DeepRecurse.visited.add(hashlib.sha3_256(web_content.url.encode("utf-8")).hexdigest())
                raise ValueError(self.web_content.error)
            elif not web_content.plain_urls():
                raise ValueError("We could not find any sub-URLs")

    def recurse(self, explorer=None):
        if self.depth > self.max_depth:
            explorer["valid_urls"].mini_loader.stop_load()
            return
        for link in self.web_content.plain_urls():
            if hashlib.sha3_256(link.encode("utf-8")).hexdigest() in DeepRecurse.visited:
                continue
            DeepRecurse.visited.add(hashlib.sha3_256(link.encode("utf-8")).hexdigest())
            content = WebContent(link, self.web_content.options)
            if content.is_valid:
                self.children[link] = DeepRecurse(content, self, self.depth + 1, max_depth=self.max_depth)
                if self.depth == 1 and explorer:
                    explorer["valid_urls"].push(self.children[link])
                self.children[link].recurse(explorer)
            elif explorer and not content.is_valid:
                explorer["invalid_urls"].push(content)

    def search(self, explorer=None, *keywords):
        if self.depth > self.max_depth:
            explorer["valid_urls"].mini_loader.stop_load()
            if not DeepRecurse.matches and explorer:
                explorer["valid_urls"].show_error("No matches for the keywords entered found")
            return
        if any([re.search(i, self.web_content.content) for i in keywords]):
            explorer["valid_urls"].push_search_item(self)
        for link in self.web_content.plain_urls():
            print(link)
            if hashlib.sha3_256(link.encode("utf-8")).hexdigest() in DeepRecurse.visited:
                continue
            DeepRecurse.visited.add(hashlib.sha3_256(link.encode("utf-8")).hexdigest())
            content = WebContent(link, self.web_content.options)
            if content.is_valid:
                DeepRecurse(content, self, self.depth + 1, max_depth=self.max_depth).search(explorer, *keywords)
            elif explorer and not content.is_valid:
                explorer["invalid_urls"].push(content)

    def start_search(self, explorer=None, *keywords):
        DeepRecurse.visited = set()
        DeepRecurse.matches = set()
        self.search(explorer, *keywords)

    def start_recurse(self, explorer=None):
        DeepRecurse.visited = set()
        DeepRecurse.matches = set()
        self.recurse(explorer)

    def links(self):
        for link in self.children.keys():
            print("  " * self.depth, link, self.children[link].web_content.title())
            self.children[link].links()


class WebContent:
    url_regex = {
        "header": r"(?P<header>http(?:s?)://(?P<host>[^/]*))(?P<path>(?:/.*)*)",
        "url": r"https?://[^/]*(?:/[^\s]*)*",
        "uri": r"(?:/[^\W]+/[^\s>]+)+[^\W]",
        "file": r".*/(?P<terminal>[^/]+\.(?P<extension>.+))+",
        "title": r".*<title>(?P<title>.+)</title>.*",
    }

    def __init__(self, url, options):
        self.options = options
        self.__request = urllib.request.Request(url, None, options)
        self.is_valid = True
        self.error = None
        try:
            self.__content = str(urllib.request.urlopen(self.__request).read().decode("utf-8"))
        except Exception as e:
            self.is_valid = False
            self.__content = ""
            self.error = e
            print(e)

    @property
    def content(self):
        return self.__content

    @property
    def url(self):
        return self.__request.full_url

    @property
    def header(self):
        return re.match(WebContent.url_regex["header"], self.__request.get_full_url()).group("header")

    def title(self):
        match = re.search(WebContent.url_regex["title"], self.content)
        if match:
            return match.group("title")
        else:
            return "Unknown"

    def urls(self):
        stream = self.__content
        matches = re.findall(WebContent.url_regex["header"], str(stream))
        print(*matches, sep="\n")

    @staticmethod
    def join(base, path):
        path = path[1:] if path.startswith("/") else path
        return "/".join([base, path])

    def append_header(self, path):
        if not path.startswith(self.header):
            return self.join(self.header, path)
        else:
            return path

    @staticmethod
    def not_file(path):
        if re.match(WebContent.url_regex["file"], path):
            if not re.match(WebContent.url_regex["file"], path).group("terminal").endswith("html"):
                return False
            else:
                return True
        else:
            return True

    @property
    def files(self):
        if not self.is_valid:
            return []
        matches = re.findall(WebContent.url_regex["uri"], self.content)
        matches = list(filter(lambda url: re.search(WebContent.url_regex["file"], url), matches))
        return list(map(self.append_header, matches))

    def plain_urls(self, ignore_files=True):
        if not self.is_valid:
            return []
        matches = re.findall(WebContent.url_regex["uri"], self.content)
        if ignore_files:
            matches = list(filter(self.not_file, matches))
        matches = list(map(self.append_header, matches))
        return matches


if __name__ == "__main__":
    sonar = DeepRecurse(WebContent(
        "http://127.0.0.1:8000/table/creator/ECE/1",
        {"User-Agent": "Mozilla/5.0"}), max_depth=5)
    sonar.recurse()
    print(sonar.web_content.files)
