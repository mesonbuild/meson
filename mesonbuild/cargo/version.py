# SPDX-License-Identifier: Apache-2.0
# Copyright © 2022-2023 Intel Corporation

"""Convert Cargo versions into Meson compatible ones."""

from __future__ import annotations
import typing as T


def api(version: str) -> str:
    # x.y.z -> x
    # 0.x.y -> 0.x
    # 0.0.x -> 0
    vers = version.split('.')
    if int(vers[0]) != 0:
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


def convert(cargo_ver: str) -> T.List[str]:
    """Return a function that checks a Version against a Cargo version
       requirement.

    :param cargo_ver: The version, as Cargo specifies
    :return: A list of version constraints, as Meson understands them
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

    return out
