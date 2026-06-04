from __future__ import annotations

import typing as T

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.domains import Domain
from sphinx.util import logging
from sphinx.util.docutils import SphinxRole

logger = logging.getLogger(__name__)


_SINCE_CLASSES = (
    'd-inline-flex mb-1 px-1 fw-semibold small text-nowrap '
    'text-success-emphasis bg-success-subtle '
    'border border-success-subtle rounded-2'
)

_DEPRECATED_CLASSES = (
    'd-inline-flex mb-1 px-1 fw-semibold small text-nowrap '
    'text-warning-emphasis bg-warning-subtle '
    'border border-warning-subtle rounded-2'
)

_OPTIONAL_CLASSES = (
    'd-inline-flex mb-1 px-1 fw-semibold small text-nowrap '
    'text-secondary-emphasis bg-secondary-subtle '
    'border border-secondary-subtle rounded-2'
)


class MesonSinceRole(SphinxRole):
    """Renders :meson:since:`x.y.z` as a styled Bootstrap badge."""

    def run(self) -> T.Tuple[T.List[nodes.Node], T.List[nodes.system_message]]:
        html = f'<span class="{_SINCE_CLASSES}">Since {self.text}</span>'
        return [nodes.raw('', html, format='html')], []


class MesonDeprecatedRole(SphinxRole):
    """Renders :meson:deprecated:`x.y.z` as a styled Bootstrap badge."""

    def run(self) -> T.Tuple[T.List[nodes.Node], T.List[nodes.system_message]]:
        html = f'<span class="{_DEPRECATED_CLASSES}">Deprecated since {self.text}</span>'
        return [nodes.raw('', html, format='html')], []


class MesonOptionalRole(SphinxRole):
    """Renders :meson:optional:`` as a styled Bootstrap badge."""

    def run(self) -> T.Tuple[T.List[nodes.Node], T.List[nodes.system_message]]:
        html = f'<span class="{_OPTIONAL_CLASSES}">optional</span>'
        return [nodes.raw('', html, format='html')], []


class MesonDomain(Domain):
    name = 'meson'
    label = 'Meson'

    roles = {
        'since':      MesonSinceRole(),
        'deprecated': MesonDeprecatedRole(),
        'optional':   MesonOptionalRole(),
    }

    directives: T.Dict[str, T.Any] = {}


def setup(app: Sphinx) -> T.Dict[str, T.Any]:
    app.add_domain(MesonDomain)

    return {
        'version': '1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
