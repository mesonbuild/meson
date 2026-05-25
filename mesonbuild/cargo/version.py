# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2023 Intel Corporation

"""Convert Cargo versions into Meson compatible ones."""

from __future__ import annotations
from functools import lru_cache
from ..mesonlib import version_compare
import operator
import re
import typing as T

from ..mesonlib import MesonException

def _api_of(version: str) -> str:
    # x.y.z -> x
    # 0.x.y -> 0.x
    # 0.0.x -> 0
    vers = version.split('.')
    if not vers[0] or int(vers[0]) != 0:
        return vers[0]
    elif len(vers) >= 2 and int(vers[1]) != 0:
        return f'0.{vers[1]}'
    return '0'


def split(cargo_ver: str) -> T.Iterable[tuple[str, str]]:
    """Canonicalization of Cargo version requirements"""
    cargo_ver = cargo_ver.strip()
    if not cargo_ver:
        return
    for ver in cargo_ver.split(','):
        ver = ver.strip()
        if ver == '*':
            continue

        if ver.startswith(('>=', '<=', '!=')):
            yield ver[0:2], ver[2:].lstrip()
        elif ver.startswith(('~', '=', '^', '>', '<')):
            yield ver[0], ver[1:].lstrip()
        elif ver.endswith('.*'):
            # asterisk requirements are same as tilde: 1.* == ~1
            # https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#wildcard-requirements
            yield '~', ver[:-2].lstrip()
        else:
            # caret requirement is the default strategy
            yield '^', ver


def api(cargo_ver: str) -> str:
    """Determine the API version implied by a Cargo version requirement.

    :param cargo_ver: A Cargo version string.
    :return: empty string if no lower bound establishes an API, otherwise the
        major version (or ``"0.x"`` / ``"0"`` for 0.x.y / 0.0.x versions).
        Raise exception if constraints disagree on the API.
    """
    apis: T.Set[str] = set()
    for op, ver in split(cargo_ver):
        if op in {'>=', '=', '^', '~'}:
            apis.add(_api_of(ver))
    if not apis:
        return ''
    elif len(apis) == 1:
        return apis.pop()
    else:
        raise MesonException(f'Cannot determine API version from {cargo_ver!r}.')


# Tokens: a digit run, an alphanumeric-with-hyphens identifier (covers the
# leading ``-`` of the pre-release section and identifiers within it), or the
# ``+`` that introduces build metadata.
_SEMVER_TOK_RE = re.compile(r'(\d+)|([A-Za-z-][0-9A-Za-z-]*)|(\+.*)')


class SemVer:
    """A SemVer 2.0.0 version, suitable for ordering.

    Adapted from ``mesonlib.Version`` but with the int/str precedence
    reversed: SemVer says numeric pre-release identifiers sort *below*
    alphanumeric ones, whereas Meson's ``Version`` does the opposite.

    Versions are represented as a flat list:
    [major, minor, patch, 0]                  for normal versions
    [major, minor, patch, -1, *pre_idents]    for pre-releases

    The fourth slot (0 for normal, -1 for pre-release) makes a normal
    version sort *above* the corresponding pre-release.
    Missing minor/patch components default to 0.
    """

    __slots__ = ('_v', 'specified_count')

    def __init__(self, in_: str | list[int | str] = None) -> None:
        vec: list[int | str]
        if isinstance(in_, str):
            vec = []
            pre = False
            specified_count = 0
            for m in _SEMVER_TOK_RE.finditer(in_):
                if m.group(1):
                    if pre or specified_count < 3:
                        vec.append(int(m.group(1)))
                        if not pre:
                            specified_count += 1
                elif m.group(2):
                    ident = m.group(2)
                    if not pre:
                        # The leading ``-`` is just a section marker.
                        if ident.startswith('-'):
                            ident = ident[1:]
                            if not ident:
                                continue
                        while len(vec) < 3:
                            vec.append(0)
                        vec.append(-1)
                        pre = True
                    vec.append(ident)
                else:
                    break  # +build metadata: discard the rest
        else:
            # Direct construction from a pre-built component list.
            vec = list(in_)
            specified_count = min(3, len(in_))

        while len(vec) < 4:
            vec.append(0)
        self._v = vec
        self.specified_count = specified_count

    def __repr__(self) -> str:
        s = '.'.join(str(c) for c in self._v[:self.specified_count])
        if len(self._v) > 4:
            s += '-' + '.'.join(str(c) for c in self._v[4:])
        return f'<SemVer: {s}>'

    @property
    def has_prerelease(self) -> bool:
        return self._v[3] == -1

    def __lt__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self.__cmp(other._v, operator.lt)
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self.__cmp(other._v, operator.gt)
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self.__cmp(other._v, operator.le)
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self.__cmp(other._v, operator.ge)
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self._v == other._v
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(other, SemVer):
            return self._v != other._v
        return NotImplemented

    def __cmp(self, other: list[int | str], comparator: T.Callable[[T.Any, T.Any], bool]) -> bool:
        for ours, theirs in zip(self._v, other):
            ours_is_int = isinstance(ours, int)
            theirs_is_int = isinstance(theirs, int)
            if ours_is_int != theirs_is_int:
                # SemVer: int (numeric) < str (alphanumeric).
                return comparator(theirs_is_int, ours_is_int)
            if ours != theirs:
                return comparator(ours, theirs)
        # "A larger set of pre-release fields has a higher precedence."
        return comparator(len(self._v), len(other))

    def next_ver(self, bump_idx: int) -> SemVer:
        """Return a new SemVer with the component at ``bump_idx`` (0=major,
        1=minor, 2=patch) bumped, following normal-version components zeroed,
        and any pre-release dropped."""
        v = list(self._v[:3])
        last = v[bump_idx]
        assert isinstance(last, int)
        v[bump_idx] = last + 1
        for i in range(bump_idx + 1, 3):
            v[i] = 0
        return SemVer(v)


@lru_cache(maxsize=None)
def cargo_parse(cargo_ver: str) -> T.Callable[[str], bool]:
    """Return a function that checks a Version against a Cargo version
       requirement.

    :param cargo_ver: The version, as Cargo specifies
    :return: A function returning true if the version is accepted.
    """
    out: T.List[str] = []
    for op, ver in split(cargo_ver):
        # https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#comparison-requirements
        # <= 3 allows 3.0.0 where meson version compare does not
        # So change <= into < with a bumped version
        if op == '<=':
            v = ver.split('.')
            if len(v) == 1:
                out.append(f'< {int(v[0]) + 1}')
            elif len(v) == 2:
                out.append(f'< {v[0]}.{int(v[1]) + 1}')
            else:
                out.append(f'{op} {ver}')

        elif op == '~':
            # Tilde requirements are the same as asterisk, so 1.* == ~1
            # https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#tilde-requirements
            # we convert those into a pair of constraints
            v = ver.split('.')
            out.append(f'>= {".".join(v)}')
            if len(v) == 3:
                out.append(f'< {v[0]}.{int(v[1]) + 1}.0')
            elif len(v) == 2:
                out.append(f'< {v[0]}.{int(v[1]) + 1}')
            else:
                out.append(f'< {int(v[0]) + 1}')

        elif op == '^':
            # Allow changes after the first non-zero version
            # That means that if this is `1.1.0``, then we need `>= 1.1.0` && `< 2.0.0`
            # Or if we have `0.1.0`, then we need `>= 0.1.0` && `< 0.2.0`
            # Or if we have `0.1`, then we need `>= 0.1.0` && `< 0.2.0`
            # Or if we have `0.0.0`, then we need `< 1.0.0`
            # Or if we have `0.0`, then we need `< 1.0.0`
            # Or if we have `0`, then we need `< 1.0.0`
            # Or if we have `0.0.3`, then we need `>= 0.0.3` && `< 0.0.4`
            # https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html#specifying-dependencies-from-cratesio
            #
            # this works much like the ~ versions, but in reverse. Tilde starts
            # at the patch version and works up, to the major version, while
            # bare numbers start at the major version and work down to the patch
            # version
            vers = ver.split('.')
            min_: T.List[str] = []
            max_: T.List[str] = []
            bumped = False
            for v_ in vers:
                if v_ != '0' and not bumped:
                    min_.append(v_)
                    max_.append(str(int(v_) + 1))
                    bumped = True
                else:
                    min_.append(v_)
                    if not bumped:
                        max_.append('0')

            # If there is no minimum, don't emit one
            if set(min_) != {'0'}:
                out.append('>= {}'.format('.'.join(min_)))
            if set(max_) != {'0'}:
                out.append('< {}'.format('.'.join(max_)))
            else:
                out.append('< 1')

        else:
            out.append(f'{op} {ver}')

    def compare(ver: str) -> bool:
        return all(version_compare(ver, comparison) for comparison in out)

    if not out:
        return lambda v: True
    return compare
