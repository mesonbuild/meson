from __future__ import annotations

from pathlib import Path
import re
import typing as T

# Maps filename language suffixes to human-readable labels used in the nav.
_LANG_LABELS: T.Dict[str, str] = {
    'zh':   '中文',
    'ptbr': 'Português',
}

from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)


def _parse_sitemap(text: str) -> T.Dict[str, T.List[str]]:
    """Return a mapping of filename -> direct children filenames."""
    result: T.Dict[str, T.List[str]] = {}
    # Each entry is (indent_level, filename).
    stack: T.List[T.Tuple[int, str]] = []

    for line in text.splitlines():
        if not line.strip():
            continue
        depth = len(line) - len(line.lstrip('\t'))
        name = line.strip()

        # Pop entries that are not an ancestor of the current line.
        while stack and stack[-1][0] >= depth:
            stack.pop()

        if stack:
            parent = stack[-1][1]
            result.setdefault(parent, []).append(name)

        stack.append((depth, name))

    return result


def _load_sitemap(app: Sphinx) -> None:
    sitemap_file: T.Optional[str] = app.config.sphinx_sitemap_file
    if not sitemap_file:
        logger.warning('sphinx_sitemap_file not configured; toctrees will not be injected')
        app.env.sitemap_children = {}  # type: ignore[attr-defined]
        return

    path = Path(sitemap_file)
    if not path.is_absolute():
        path = Path(app.confdir) / path

    app.env.sitemap_children = _parse_sitemap(path.read_text(encoding='utf-8'))  # type: ignore[attr-defined]
    logger.info('Sphinx sitemap loaded from %s', path)


def _inject_toctree(app: Sphinx, docname: str, source: T.List[str]) -> None:
    children_map: T.Dict[str, T.List[str]] = getattr(app.env, 'sitemap_children', {})

    # The sitemap uses bare filenames; docname has no extension.
    children = children_map.get(docname + '.md')
    if not children:
        return

    # Strip .md so Sphinx resolves them as doc names.
    # For release-note pages, use an explicit "version <docname>" title so the
    # nav label shows just the version number without the page needing its own
    # visible version heading.
    def _entry(filename: str) -> str:
        docname = filename.removesuffix('.md')

        # Release notes: "1.11.0 <Release-notes-for-1.11.0>"
        m = re.fullmatch(r'Release-notes-for-(.+)', docname)
        if m:
            return f'{m.group(1)} <{docname}>'

        # Translations: "Base Title (Language) <Base-name_langcode>"
        # Pattern: {base}_{langcode} where langcode is in _LANG_LABELS.
        m = re.fullmatch(r'(.+)_([a-z]+)', docname)
        if m:
            lang_label = _LANG_LABELS.get(m.group(2))
            if lang_label:
                base_title = m.group(1).replace('-', ' ').title()
                return f'{base_title} ({lang_label}) <{docname}>'

        return docname

    entries = '\n'.join(_entry(c) for c in children)
    toctree = f'\n\n```{{toctree}}\n:hidden:\n\n{entries}\n```\n'
    source[0] += toctree


def setup(app: Sphinx) -> T.Dict[str, T.Any]:
    app.add_config_value('sphinx_sitemap_file', default=None, rebuild='env')
    app.connect('builder-inited', _load_sitemap)
    app.connect('source-read', _inject_toctree)

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
