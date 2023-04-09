from __future__ import annotations
import re
from typing import Dict, List, Any, Optional, Generator, Callable
from bs4 import BeautifulSoup
from .exceptions import PageError, RedirectError, ODD_ERROR_MESSAGE


class MemoryTauPage(object):
    """
    Contains data from a Memory Tau page.
    Uses property methods to filter data from the raw HTML.
    """

    def __init__(
        self,
        request: Callable[
            [Dict[str, Any]],
            Dict[str, Any],
        ],
        title: Optional[str] = None,
        pageid: Optional[int] = None,
        redirect: bool = True,
        preload: bool = False,
        original_title: str = "",
    ) -> None:
        self._markdown = None
        self._backlinks = None
        self._backlinks_ids = None
        self._categories = None
        self._content = None
        self._html = None
        self._links = None
        self._parent_id = None
        self._references = None
        self._revision_id = None
        self._sections = None
        self._summary = None
        if title is not None:
            self.title: str = title
            self.original_title: str = original_title or title
        elif pageid is not None:
            self.pageid: int = pageid
        else:
            raise ValueError("Either a title or a pageid must be specified")

        self.request = request
        self.__load(redirect=redirect, preload=preload)
        if preload:
            for prop in (
                "content",
                "summary",
                "images",
                "references",
                "links",
                "sections",
                "infobox",
            ):
                getattr(self, prop)

    def __repr__(self) -> str:
        return "<WikipediaPage {}>".format(self.title)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MemoryTauPage):
            return NotImplemented
        try:
            return (
                self.pageid == other.pageid
                and self.title == other.title
                and self.url == other.url
            )
        except Exception:
            return False

    def __load(self, redirect: bool = True, preload: bool = False) -> None:
        """
        Load basic information from Memory Tau.
        Confirm that page exists and is not a disambiguation/redirect.

        Does not need to be called manually, should be called automatically during __init__.
        """
        query_params: Dict[str, str | int] = {
            "prop": "info|pageprops",
            "inprop": "url",
            "redirects": "",
        }
        if not getattr(self, "pageid", None):
            query_params["titles"] = self.title
        else:
            query_params["pageids"] = self.pageid

        request = self.request(query_params)

        query = request["query"]
        pageid = list(query["pages"].keys())[0]
        page = query["pages"][pageid]

        # missing is present if the page is missing
        if "missing" in page:
            if hasattr(self, "title"):
                raise PageError(title=self.title)
            else:
                raise PageError(pageid=self.pageid)

        # same thing for redirect, except it shows up in query instead of page for
        # whatever silly reason
        elif "redirects" in query and page["title"] != query["redirects"][0]["to"]:
            if redirect:
                redirects = query["redirects"][0]
                if "normalized" in query:
                    normalized = query["normalized"][0]
                    assert normalized["from"] == self.title, ODD_ERROR_MESSAGE
                    from_title = normalized["to"]

                elif hasattr(self, "title"):
                    from_title = self.title
                else:
                    from_title = redirects["from"]

                assert redirects["from"] == from_title, ODD_ERROR_MESSAGE

                # change the title and reload the whole object
                # TODO this should be refactored
                self.__init__(
                    redirects["to"],
                    redirect=redirect,
                    preload=preload,
                    request=self.request,
                )

            else:
                raise RedirectError(getattr(self, "title", page["title"]))

        self.pageid = pageid
        self.title = page.get("title")
        self.url: str = page.get("fullurl")
        self.pageprops: Dict[str, Any] = page.get("pageprops", {})
        self.disambiguate_pages: List[Any] = []

        # since we only asked for disambiguation in ppprop,
        # if a pageprop is returned,
        # then the page must be a disambiguation page
        if "pageprops" in page and "disambiguation" in page["pageprops"]:
            query_params = {
                "prop": "revisions",
                "rvprop": "content",
                "rvlimit": 1,
            }
            if hasattr(self, "pageid"):
                query_params["pageids"] = self.pageid
            else:
                query_params["titles"] = self.title
            request = self.request(query_params)
            html = request["query"]["pages"][pageid]["revisions"][0]["*"]
            lis = BeautifulSoup(html, "html.parser").find_all("li")
            filtered_lis = [
                li for li in lis if "tocsection" not in "".join(li.get("class", []))
            ]
            for lis_item in filtered_lis:
                items = lis_item.find_all("a")
                if items:
                    self.disambiguate_pages.append(items[0]["title"])

    def __continued_query(
        self, query_params: Dict[str, Any]
    ) -> Generator[Any, None, None]:
        """
        Based on https://www.mediawiki.org/wiki/API:Query#Continuing_queries
        """
        query_params.update(self.__title_query_param)

        last_continue: Dict[str, Any] = {}
        last_len_pages: int = 0
        prop = query_params.get("prop", None)
        while True:
            params = query_params.copy()
            params.update(last_continue)
            request = self.request(params)
            if "query" not in request:
                break

            if (
                "continue" in request
                and last_continue == request["continue"]
                and last_len_pages == len(request["query"]["pages"])
            ):
                break
            pages = request["query"]["pages"]
            if "generator" in query_params:
                yield from pages.values()
            else:
                if prop in pages[self.pageid]:
                    for datum in pages[self.pageid][prop]:
                        yield datum

            if "continue" not in request:
                break

            last_continue = request["continue"]
            last_len_pages = len(request["query"]["pages"])

    @property
    def __title_query_param(self) -> Dict[str, str | int]:
        if getattr(self, "title", None) is not None:
            return {"titles": self.title}
        else:
            return {"pageids": self.pageid}

    def html(self) -> Any:
        """
        Get full page HTML.

        Warning: This can get pretty slow on long pages.
        """
        if not getattr(self, "_html", False):
            query_params = {
                "action": "parse",
                "page": self.title,
                "prop": "text",
                "formatversion": 2,
            }

            request = self.request(query_params)
            self._html = request["parse"]["text"]

        return self._html

    def markdown(self) -> Any:
        """
        Get full page markdown.

        Warning: This can get pretty slow on long pages.
        """
        if not getattr(self, "_markdown", False):
            query_params = {
                "action": "parse",
                "page": self.title,
                "prop": "wikitext",
                "formatversion": 2,
            }

            request = self.request(query_params)
            self._markdown = request["parse"]["wikitext"]

        return self._markdown

    @property
    def content(self) -> str:
        """
        Plain text content of the page, excluding images, tables, and other data.
        """
        if not getattr(self, "_content", False):
            query_params: Dict[str, str | int] = {
                "prop": "extracts|revisions",
                "explaintext": "",
                "rvprop": "ids",
            }
            query_params.update(self.__title_query_param)
            request = self.request(query_params)
            self._content: str = request["query"]["pages"][self.pageid]["extract"]
            self._revision_id: int = request["query"]["pages"][self.pageid][
                "revisions"
            ][0]["revid"]
            self._parent_id: int = request["query"]["pages"][self.pageid]["revisions"][
                0
            ]["parentid"]

        return self._content

    # noinspection PyStatementEffect
    @property
    def revision_id(self) -> int:
        """
        Revision ID of the page.

        The revision ID is a number that uniquely identifies the current
        version of the page. It can be used to create the permalink or for
        other direct API calls. See `Help:Page history
        <https://www.mysidia.org/trekwiki/Wikipedia:Revision>`_ for more
        information.
        """
        if not getattr(self, "_revid", False):
            # fetch the content (side effect is loading the revid)
            self.content

        return self._revision_id

    # noinspection PyStatementEffect
    @property
    def parent_id(self) -> int:
        """
        Revision ID of the parent version of the current revision of this page.
        See ``revision_id`` for more information.
        """
        if not getattr(self, "_parentid", False):
            # fetch the content (side effect is loading the revid)
            self.content
        return self._parent_id

    @property
    def summary(self) -> str:
        """
        Plain text summary of the page.
        """
        if not getattr(self, "_summary", False):
            query_params: Dict[str, str | int] = {
                "prop": "extracts",
                "explaintext": "",
                "exintro": "",
            }
            query_params.update(self.__title_query_param)

            request = self.request(query_params)
            self._summary: str = request["query"]["pages"][self.pageid]["extract"]

        return self._summary

    @property
    def references(self) -> List[str]:
        """
        List of URLs of external links on a page.
        May include external links within page that aren't technically cited anywhere.
        """
        if not getattr(self, "_references", False):

            def add_protocol(url: str) -> str:
                return url if url.startswith("http") else "http:" + url

            self._references = [
                add_protocol(link["*"])
                for link in self.__continued_query(
                    {"prop": "extlinks", "ellimit": "max"}
                )
            ]

        return self._references

    @property
    def links(self) -> List[str]:
        """
        List of titles of Wikipedia page links on a page.

        Note: Only includes articles from namespace 0, meaning no Category, User talk,
            or other meta-Wikipedia pages.
        """
        if not getattr(self, "_links", False):
            self._links = [
                link["title"]
                for link in self.__continued_query(
                    {"prop": "links", "plnamespace": 0, "pllimit": "max"}
                )
            ]

        return self._links

    @property
    def backlinks(self) -> List[str]:
        """
        List of pages that link to a given page
        """
        if not getattr(self, "_backlinks", False):
            links = [
                link
                for link in self.__continued_query(
                    {
                        "list": "backlinks",
                        "generator": "links",
                        "bltitle": self.__title_query_param,
                        "blfilterredir": "redirects",
                    }
                )
            ]
            self._backlinks = [link["title"] for link in links]
            self._backlinks_ids = [link["pageid"] for link in links if "pageid" in link]
        return self._backlinks

    @property
    def backlinks_ids(self) -> List[int]:
        """
        List of pages ids that link to a given page

        Note: It is not guaranteed that backlinks_ids list contains all backlinks.
            Sometimes the pageid is missing and only title is available, as a result
            len(backlinks_ids) <= len(backlinks).
        """
        if not getattr(self, "_backlinks_ids", False):
            getattr(self, "backlinks")
        return self._backlinks_ids

    @property
    def categories(self) -> List[str]:
        """
        List of categories of a page.
        """
        if not getattr(self, "_categories", False):
            self._categories = [
                re.sub(r"^Category:", "", x)
                for x in [
                    link["title"]
                    for link in self.__continued_query(
                        {"prop": "categories", "cllimit": "max"}
                    )
                ]
            ]

        return self._categories

    @property
    def sections(self) -> List[str]:
        """
        List of section titles from the table of contents on the page.
        """
        if not getattr(self, "_sections", False):
            query_params: Dict[str, str | int] = {
                "action": "parse",
                "prop": "sections",
            }
            if getattr(self, "title", None) is not None:
                query_params.update({"page": self.title})
            else:
                query_params.update({"pageid": self.pageid})

            request = self.request(query_params)
            self._sections = [
                section["line"] for section in request["parse"]["sections"]
            ]

        return self._sections

    def section(self, section_title: str) -> Optional[str]:
        """
        Get the plain text content of a section from `self.sections`.
        Returns None if `section_title` isn't found, otherwise returns a whitespace stripped string.

        This is a convenience method that wraps self.content.

        .. warning:: Calling `section` on a section that has subheadings will NOT return
               the full text of all the subsections. It only gets the text between
               `section_title` and the next subheading, which is often empty.
        """

        section = "== {} ==".format(section_title)
        try:
            index = self.content.index(section) + len(section)
        except ValueError:
            return None

        try:
            next_index = self.content.index("==", index)
        except ValueError:
            next_index = len(self.content)

        return self.content[index:next_index].lstrip("=").strip()
