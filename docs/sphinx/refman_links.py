from __future__ import annotations

from json import loads
from pathlib import Path
import re
import typing as T

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

_LINK_RE = re.compile(
    r'(\[\[#?@?([ \n\t]*[a-zA-Z0-9_]+[ \n\t]*\.)*[ \n\t]*[a-zA-Z0-9_]+[ \n\t]*\]\])(.?)',
    re.MULTILINE,
)


def _load_refman_data(app: Sphinx) -> None:
    data_file: T.Optional[str] = app.config.refman_data_file
    if not data_file:
        logger.info('Meson refman extension DISABLED (no refman_data_file configured)')
        app.env.refman_data = {}  # type: ignore[attr-defined]
        return

    path = Path(data_file)
    if not path.is_absolute():
        path = Path(app.confdir) / path

    app.env.refman_data = loads(path.read_text(encoding='utf-8'))  # type: ignore[attr-defined]
    logger.info('Meson refman extension LOADED')


def _replace_links(app: Sphinx, docname: str, source: T.List[str]) -> None:
    data: T.Dict[str, str] = getattr(app.env, 'refman_data', {})
    if not data:
        return

    def _replace(m: 're.Match[str]') -> str:
        link_tag = m.group(1)   # [[...]]
        next_char = m.group(3)  # character immediately after ]]

        obj_id: str = link_tag[2:-2]
        obj_id = re.sub(r'[ \n\t]', '', obj_id)

        in_code_block = obj_id.startswith('#')
        if in_code_block:
            obj_id = obj_id[1:]

        if obj_id not in data:
            logger.warning('%s: Unknown Meson refman link: "%s"', docname, obj_id)
            return m.group(0)

        url = data[obj_id]

        # [[!key]] — replace with the raw URL only (no link markup)
        if obj_id.startswith('!'):
            return url + next_char

        text = obj_id
        if text.startswith('@'):
            text = text[1:]
        elif in_code_block:
            if next_char != '(':
                text += '()'
        else:
            text += '()'

        # Links inside Markdown headings produce nested <a> elements (the TOC
        # wraps each heading in its own <a>), which is invalid HTML and breaks
        # slug generation.  Emit plain text only.
        line_start = source[0].rfind('\n', 0, m.start()) + 1
        if source[0][line_start:m.start()].lstrip().startswith('#'):
            return f'`{text}`' + next_char

        if in_code_block:
            # Inside <pre><code> signatures — plain link, no extra wrapper.
            return f'<a href="{url}">{text}</a>' + next_char
        else:
            # Prose and HTML table cells — wrap in <code> to match the
            # monospace style used for type names and function references.
            return f'<a href="{url}"><code>{text}</code></a>' + next_char

    source[0] = _LINK_RE.sub(_replace, source[0])


def setup(app: Sphinx) -> T.Dict[str, T.Any]:
    app.add_config_value('refman_data_file', default=None, rebuild='env')
    app.connect('builder-inited', _load_refman_data)
    app.connect('source-read', _replace_links)

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
