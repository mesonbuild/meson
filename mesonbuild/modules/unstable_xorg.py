# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021 Intel Corporation

import os
import typing as T

from . import NewExtensionModule, ModuleReturnValue
from .. import mesonlib
from ..build import InvalidArguments, CustomTarget
from ..interpreterbase import FeatureNew, KwargInfo, typed_kwargs, typed_pos_args

if T.TYPE_CHECKING:
    from . import ModuleState
    from ..interpreter import Interpreter

    from typing_extensions import TypedDict

    class FormatManKW(TypedDict):

        apploaddir: T.Optional[str]


__all__ = ['initialize']

# This has been vastily simplified to only be accurate for xorg's purposes. If
# this were to be used generally there would be bugs. In particualar the "sysv"
# section is more accurately "old solaris/sunos"
_MAN_SECTIONS = {
    'traditional': {
        'app': '1',
        'driver': '4',
        'admin': '8',
        'lib': '3',
        'misc': '7',
        'file': '5',
    },
    'sysv': {
        'app': '1',
        'driver': '7',
        'admin': '1m',
        'lib': '3',
        'misc': '5',
        'file': '4',
    }
}


class XorgModule(NewExtensionModule):

    """Module for upstream xorg development.

    This module contains helper and abstractions for upstream xorg projects to
    use. These are *not* meant for projects using X11, though they might be
    useful in that case.
    """

    def __init__(self) -> None:
        super().__init__()
        self.methods.update({
            'format_man': self.format_man_method,
        })

    def _uses_sysv_man_sections(self) -> bool:
        """Returns true if using sysv man sections."""
        # XXX: This is only correct for build == host
        # Copied from xorg-macros
        return os.path.exists('/usr/share/man/man7/attributes.7')

    @typed_pos_args('xorg.format_man', (str, mesonlib.File), str)
    @typed_kwargs('xorg.format_man', KwargInfo('apploaddir', str, default=''))
    def format_man_method(self, state: 'ModuleState', args: T.Tuple['mesonlib.FileOrString', str],
                          kwargs: 'FormatManKW') -> ModuleReturnValue:
        """Create a custom target that formats a man file.

        This provides several nice features:
        1. It knows about different man sections, which means that you don't
           have to guess about sysv vs old unix layouts
        2. it automatically sets some constant data (there's only one X server
           at this point, and it's not going to bump to version 12 most likely)
        3. it validates the sections

        if the `apploaddir` keyword argument is unset then this will set any
        __apploaddir__ values to an empty string.
        """
        key = state.environment.coredata.get_option(
            key = mesonlib.OptionKey('man-sections', module='xorg'))
        assert isinstance(key, str), 'for mypy'
        if key == 'auto':
            key = 'sysv' if self._uses_sysv_man_sections() else 'traditional'
        sections = _MAN_SECTIONS[key]

        rules: T.List[T.Tuple[str, str]] = [
            ('__adminmansuffix__', sections['admin']),
            ('__apploaddir__', kwargs['apploaddir']),
            ('__appmansuffix__', sections['app']),
            ('__drivermansuffix__', sections['driver']),
            ('__filemansuffix__', sections['file']),
            ('__libmansuffix__', sections['lib']),
            ('__miscmansuffix__', sections['misc']),
            ('__projectroot__', state.environment.get_prefix()),
            ('__vendorversion__', f'"{state.project_version}" "X Version 11"'),
            ('__xconfigfile__', 'xorg.conf'),
            ('__xorgversion__', f'"{state.project_name} {state.project_version}" "X Version 11"'),
            ('__xservername__', 'Xorg'),
        ]

        infile, section = args
        if section not in sections:
            raise InvalidArguments(
                f'xorg.format_man() second argument must be one of "{", ".join(sorted(sections))}", not "{section}"')

        if isinstance(infile, str):
            # In case this is passed in the form `man/foo.man`
            name = os.path.basename(infile)
        else:
            name = infile.fname

        rule_cmd: T.List[str] = []
        for r in rules:
            rule_cmd.append('--regex')
            rule_cmd.extend(r)

        ct = CustomTarget(
            f'Xorg man page {os.path.splitext(name)[0]}.{sections[section]}',
            state.subdir,
            state.subproject,
            state.environment,
            state.environment.get_build_command() + ['--internal', 'regex_replace', '@INPUT@', '@OUTPUT@'] + rule_cmd,
            [infile],
            [f'@BASENAME@.{sections[section]}'],
            build_by_default=True,
            install=True,
            install_dir=[os.path.join(state.environment.get_mandir(), f'man{sections[section]}')],
        )

        return ModuleReturnValue(ct, [ct])


def initialize(interp: 'Interpreter') -> XorgModule:
    FeatureNew.single_use('xorg-devel module', '0.64.0', interp.subproject)
    return XorgModule()
