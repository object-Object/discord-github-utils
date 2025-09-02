import re
from typing import override

from marko import Markdown
from marko.block import HTMLBlock
from marko.ext.gfm import GFM
from marko.inline import Image, InlineHTML
from marko.md_renderer import MarkdownRenderer


class DiscordMarkdownRenderer(MarkdownRenderer):
    @override
    def render_html_block(self, element: HTMLBlock) -> str:
        return _strip_html_comments(super().render_html_block(element))

    @override
    def render_inline_html(self, element: InlineHTML) -> str:
        return _strip_html_comments(super().render_inline_html(element))

    @override
    def render_image(self, element: Image) -> str:
        return super().render_image(element).removeprefix("!")


_HTML_COMMENT_PATTERN = re.compile(r"<!--.*?-->", flags=re.DOTALL)


def _strip_html_comments(text: str) -> str:
    return _HTML_COMMENT_PATTERN.sub("", text)


def reflow_markdown(text: str) -> str:
    md = Markdown(
        renderer=DiscordMarkdownRenderer,
        extensions=[GFM],
    )
    return md.convert(text)
