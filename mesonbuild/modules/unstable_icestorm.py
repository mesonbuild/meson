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

from .. import mesonlib, compilers, mlog

from . import ExtensionModule

class IceStormModule(ExtensionModule):

    def __init__(self):
        super().__init__()
        self.snippets.add('project')
        self.yosys_bin = None

    def detect_binaries(self, interpreter):
        self.yosys_bin = interpreter.func_find_program(None, ['yosys'], {})
        self.arachne_bin = interpreter.func_find_program(None, ['arachne-pnr'], {})
        self.icepack_bin = interpreter.func_find_program(None, ['icepack'], {})
        self.iceprog_bin = interpreter.func_find_program(None, ['iceprog'], {})
        self.icetime_bin = interpreter.func_find_program(None, ['icetime'], {})

    def project(self, interpreter, state, args, kwargs):
        if not self.yosys_bin:
            self.detect_binaries(interpreter)
        result = []
        if not len(args):
            raise mesonlib.MesonException('Project requires at least one argument, which is the project name.')
        proj_name = args[0]
        arg_sources = args[1:]
        if not isinstance(proj_name, str):
            raise mesonlib.MesonException('Argument must be a string.')
        kwarg_sources = kwargs.get('sources', [])
        if not isinstance(kwarg_sources, list):
            kwarg_sources = [kwarg_sources]
        all_sources = interpreter.source_strings_to_files(interpreter.flatten(arg_sources + kwarg_sources))
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
            'build_by_default' : True})

        up_target = interpreter.func_run_target(None, [upload_name], {
            'command': [self.iceprog_bin, bin_target]})

        time_target = interpreter.func_run_target(None, [time_name], {
            'command' : [self.icetime_bin, bin_target]})

def initialize():
    return IceStormModule()
