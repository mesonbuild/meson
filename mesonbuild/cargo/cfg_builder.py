# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Node builder helpers for working with cfg AST.
"""

import typing as T

from . import cfg_parser
from .. import mlog

if T.TYPE_CHECKING:
    from .cfg_parser import AST
    from .nodebuilder import NodeBuilder


# Map cargo target_os values to meson host_machine.system() values
_TARGET_OS_MAP: T.Mapping[str, str] = {
    'dragonfly': 'dragonfly',
    'freebsd': 'freebsd',
    'haiku': 'haiku',
    'illumos': 'sunos',
    'solaris': 'sunos',
    'linux': 'linux',
    'netbsd': 'netbsd',
    'openbsd': 'openbsd',
    'darwin': 'darwin',
    'android': 'android',  # this is a convetion on the meson side only, and subject to change
    'macos': 'darwin',
    'ios': 'darwin',
    'windows': 'windows',
}

# A list of Unix like OSes
# I'm sure some are missing
_UNIX_LIKE_OSES: T.FrozenSet[str] = frozenset({
    'linux',
    'android',
    'freebsd',
    'openbsd',
    'netbsd',
    'dragonfly',
    'sunos',
    'gnu',
    'cygwin',
    'darwin',
})


def build(builder: 'NodeBuilder', node: cfg_parser.FunctionNode) -> None:
    """Convert cfg_parser AST into meson AST.

    cargo/rust's cfg() syntax is a purely functional mini-langauge, with no
    side effects, in which all the functions return a boolean. This simplify
    things considerably as we just have to convert things like `any(a, b, c)`
    into `a or b or c`.
    """
    if node.name == 'cfg':
        node = node.arguments[0]

    if node.name in {'equal', 'not_equal'}:
        assert len(node.arguments) == 2
        left, right = node.arguments

        assert isinstance(left, cfg_parser.ConstantNode)
        if isinstance(right, cfg_parser.FunctionNode):
            b = builder.new()
            build(b, right)
            right = b
        else:
            assert isinstance(right, cfg_parser.StringNode)

        if left.value in {'target_os', 'target_arch'}:
            with builder.equality_builder('==' if node.name == 'equal' else '!=') as ebuilder:
                with ebuilder.left_builder() as lbuilder:
                    with lbuilder.object_builder('host_machine') as obuilder:
                        if left.value == 'target_os':
                            obuilder.method_call('system')
                        else:
                            obuilder.method_call('cpu_family')
                with ebuilder.right_builder() as lbuilder:
                    if left.value == 'target_os':
                        try:
                            v = _TARGET_OS_MAP[right.value]
                        except KeyError:
                            mlog.warning(f'Cannot map cargo os "{right.value}" to meson value. Please report this as a bug.')
                            v = 'unsupported platform'
                    else:
                        v = right.value
                        if v.startswith('powerpc'):
                            v = 'ppc64' if v.endswith('64') else 'ppc'
                        elif v.startswith('arm'):  # TODO: may be too aggressive
                            v = 'arm'
                    lbuilder.append(builder.string(v))
        elif left.value == 'target_family':
            with builder.equality_builder('in') as ebuilder:
                with ebuilder.left_builder() as lbuilder:
                    with lbuilder.object_builder('host_machine') as obuilder:
                        obuilder.method_call('system')
                with ebuilder.right_builder() as lbuilder:
                    with lbuilder.array_builder() as abuilder:
                        if right.value == 'windows':
                            abuilder.positional('windows')
                        else:
                            for o in sorted(_UNIX_LIKE_OSES):
                                abuilder.positional(o)
        else:
            raise NotImplementedError(f'config: {left.value}')
    elif node.name in {'any', 'all'}:
        i = iter(node.arguments)
        b = builder.new()
        build(b, next(i))
        with builder.logic_builder(b.finalize().lines[0]) as lbuilder:
            for o in i:
                b = builder.new()
                build(b, o)
                if node.name == 'any':
                    lbuilder.or_(b.finalize().lines[0])
                else:
                    lbuilder.and_(b.finalize().lines[0])
    else:
        raise NotImplementedError(f'function: {node}')