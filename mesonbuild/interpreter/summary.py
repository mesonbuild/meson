# SPDX-License-Identifier: Apache-2.0
# Copyright 2012-2023 The Meson development team

from __future__ import annotations

import collections
import shutil
import typing as T

from .. import mlog
from ..coredata import UserOption
from ..dependencies import Dependency
from ..interpreterbase import FeatureNew, InterpreterException
from ..interpreterbase.disabler import Disabler
from ..programs import ExternalProgram
from ..utils.universal import listify

if T.TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from .._typing import SizedStringProtocol
    from ..interpreterbase.baseobjects import SubProject

    _SummaryValueTypes: TypeAlias = T.Union[str, int, bool, ExternalProgram, Dependency, Disabler, UserOption]
    _SummaryValues: TypeAlias = T.Dict[str, T.Union[T.List[_SummaryValueTypes], _SummaryValueTypes]]
    _Loggable: TypeAlias = T.Union[SizedStringProtocol, mlog.AnsiDecorator]


class Summary:
    def __init__(self, project_name: str, project_version: str):
        self.project_name = project_name
        self.project_version = project_version
        self.sections: T.DefaultDict[str, T.Dict[str, T.Tuple[T.List[_Loggable], T.Optional[str]]]] = collections.defaultdict(dict)
        self.max_key_len = 0

    def add_section(self, section: str, values: _SummaryValues,
                    bool_yn: bool, list_sep: T.Optional[str],
                    subproject: SubProject) -> None:
        for k, v in values.items():
            if k in self.sections[section]:
                raise InterpreterException(f'Summary section {section!r} already have key {k!r}')
            formatted_values: T.List[_Loggable] = []
            i: _SummaryValueTypes
            for i in listify(v):
                if isinstance(i, bool):
                    if bool_yn:
                        formatted_values.append(mlog.green('YES') if i else mlog.red('NO'))
                    else:
                        formatted_values.append('true' if i else 'false')
                elif isinstance(i, (str, int)):
                    formatted_values.append(str(i))
                elif isinstance(i, (ExternalProgram, Dependency)):
                    FeatureNew.single_use('dependency or external program in summary', '0.57.0', subproject)
                    formatted_values.append(i.summary_value())
                elif isinstance(i, Disabler):
                    FeatureNew.single_use('disabler in summary', '0.64.0', subproject)
                    formatted_values.append(mlog.red('NO'))
                elif isinstance(i, UserOption):
                    FeatureNew.single_use('feature option in summary', '0.58.0', subproject)
                    formatted_values.append(i.printable_value())
                else:
                    m = 'Summary value in section {!r}, key {!r}, must be string, integer, boolean, dependency, disabler, or external program'
                    raise InterpreterException(m.format(section, k))
            self.sections[section][k] = (formatted_values, list_sep)
            self.max_key_len = max(self.max_key_len, len(k))

    def dump(self) -> None:
        mlog.log(self.project_name, mlog.normal_cyan(self.project_version))
        for section, values in self.sections.items():
            mlog.log('')  # newline
            if section:
                mlog.log(' ', mlog.bold(section))
            for k, rv in values.items():
                v, list_sep = rv
                padding = self.max_key_len - len(k)
                end = ' ' if v else ''
                mlog.log(' ' * 3, k + ' ' * padding + ':', end=end)
                indent = self.max_key_len + 6
                self.dump_value(v, list_sep, indent)
        mlog.log('')  # newline

    def dump_value(self, arr: T.List[_Loggable], list_sep: T.Optional[str], indent: int) -> None:
        lines_sep = '\n' + ' ' * indent
        if list_sep is None:
            mlog.log(*arr, sep=lines_sep, display_timestamp=False)
            return
        max_len = shutil.get_terminal_size().columns
        line: T.List[_Loggable] = []
        line_len = indent
        lines_sep = list_sep.rstrip() + lines_sep
        for v in arr:
            v_len = len(v) + len(list_sep)
            if line and line_len + v_len > max_len:
                mlog.log(*line, sep=list_sep, end=lines_sep)
                line_len = indent
                line = []
            line.append(v)
            line_len += v_len
        mlog.log(*line, sep=list_sep, display_timestamp=False)
