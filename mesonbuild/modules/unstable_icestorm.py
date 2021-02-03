# Copyright 2017 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import typing as T

from . import ExtensionModule
from .. import mesonlib
from ..interpreter import CustomTargetHolder, CustomTargetIndexHolder, GeneratedListHolder
from ..interpreterbase import FeatureNew
from ..interpreterbase import flatten, typed_pos_args

class IceStormModule(ExtensionModule):

    @FeatureNew('FPGA/Icestorm Module', '0.45.0')
    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.snippets.add('project')
        self.yosys_bin = None

    def detect_binaries(self, interpreter):
        self.yosys_bin = interpreter.find_program_impl(['yosys'])
        self.arachne_bin = interpreter.find_program_impl(['arachne-pnr'])
        self.icepack_bin = interpreter.find_program_impl(['icepack'])
        self.iceprog_bin = interpreter.find_program_impl(['iceprog'])
        self.icetime_bin = interpreter.find_program_impl(['icetime'])

    @typed_pos_args('icestorm.project', str, varargs=(str, mesonlib.File, CustomTargetHolder, CustomTargetIndexHolder, GeneratedListHolder), min_varargs=1)
    def project(self, interpreter, state, args: T.Tuple[str, T.List[T.Union[str, mesonlib.File, CustomTargetHolder, CustomTargetIndexHolder, GeneratedListHolder]]], kwargs):
        if not self.yosys_bin:
            self.detect_binaries(interpreter)
        proj_name = args[0]
        arg_sources = args[1]
        kwarg_sources = kwargs.get('sources', [])
        all_sources = interpreter.source_strings_to_files(flatten(arg_sources + kwarg_sources))
        if 'constraint_file' not in kwargs:
            raise mesonlib.MesonException('Constraint file not specified.')

        constraint_file = interpreter.source_strings_to_files(kwargs['constraint_file'])
        if len(constraint_file) != 1:
            raise mesonlib.MesonException('Constraint file must contain one and only one entry.')
        blif_name = proj_name + '_blif'
        blif_fname = proj_name + '.blif'
        asc_name = proj_name + '_asc'
        asc_fname = proj_name + '.asc'
        bin_name = proj_name + '_bin'
        bin_fname = proj_name + '.bin'
        time_name = proj_name + '-time'
        upload_name = proj_name + '-upload'

        blif_target = interpreter.func_custom_target(None, [blif_name], {
            'input': all_sources,
            'output': blif_fname,
            'command': [self.yosys_bin, '-q', '-p', 'synth_ice40 -blif @OUTPUT@', '@INPUT@']})

        asc_target = interpreter.func_custom_target(None, [asc_name], {
            'input': blif_target,
            'output': asc_fname,
            'command': [self.arachne_bin, '-q', '-d', '1k', '-p', constraint_file, '@INPUT@', '-o', '@OUTPUT@']})

        bin_target = interpreter.func_custom_target(None, [bin_name], {
            'input': asc_target,
            'output': bin_fname,
            'command': [self.icepack_bin, '@INPUT@', '@OUTPUT@'],
            'build_by_default': True})

        interpreter.func_run_target(None, [upload_name], {
            'command': [self.iceprog_bin, bin_target]})

        interpreter.func_run_target(None, [time_name], {
            'command': [self.icetime_bin, bin_target]})

def initialize(*args, **kwargs):
    return IceStormModule(*args, **kwargs)
