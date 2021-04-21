# SPDX-license-identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

from pathlib import Path

from mesonbuild import mparser
from mesonbuild.cargo.cfg_builder import *
from mesonbuild.cargo.cfg_parser import *
from mesonbuild.cargo.nodebuilder import NodeBuilder


class TestCfgBuilder:

    def test_eq(self) -> None:
        builder = NodeBuilder(Path(''))

        id = builder.id('host_machine')
        left = mparser.MethodNode('', 0, 0, id, 'system', mparser.ArgumentNode(builder._builder.token()))
        right = builder.string('sunos')
        expected = mparser.ComparisonNode('==', left, right)

        # use illumos to test the translation from cargo names to meson names
        ast = parse('cfg(target_os = "illumos")')
        builder = NodeBuilder(Path(''))
        build(builder, ast)
        final = builder.finalize()
        assert len(final.lines) == 1

        actual = final.lines[0]
        assert actual == expected
