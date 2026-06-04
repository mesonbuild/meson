from __future__ import annotations

from pathlib import Path
import re
import typing as T

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

# Matches {{ filename }} include directives on their own line.
_INC_RE = re.compile(r'^\{\{\s*(\S+)\s*\}\}$', re.MULTILINE)


def _replace_includes(app: Sphinx, docname: str, source: T.List[str]) -> None:
    def _find(filename: str) -> T.Optional[Path]:
        for base in (Path(app.srcdir), Path(app.confdir)):
            p = base / filename
            if p.exists():
                return p
        return None

    def _replace(m: 're.Match[str]') -> str:
        filename = m.group(1)
        path = _find(filename)
        if path is None:
            logger.warning('%s: include file not found: %s', docname, filename)
            return f'```{{warning}}\nInclude file not found: {filename}\n```'

        content = path.read_text(encoding='utf-8')

        if filename.endswith('.inc'):
            # Plain-text CLI output: usage lines become a shell block,
            # argument listings become a plain text block.
            lang = 'shell' if '_usage.' in filename else 'text'
            return f'```{lang}\n{content}\n```'

        # .md and other files: inline the content as-is so myst-parser
        # processes it normally (e.g. the WrapDB Markdown table).
        return content

    source[0] = _INC_RE.sub(_replace, source[0])


def setup(app: Sphinx) -> T.Dict[str, T.Any]:
    app.connect('source-read', _replace_includes)

    return {
        'version': '1.0',
        'parallel_read_safe': False,  # reads files from confdir, safe but sequential
        'parallel_write_safe': True,
    }
