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

from . import ModuleReturnValue
from . import ExtensionModule
from . import permittedKwargs
from .. import build
import os

class BitstreamTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class SimulationTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class AnalysisTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class FpgaLibraryTarget(build.CustomTarget):
    def __init__(self, name, subdir, packages, kwargs):
        super().__init__(name, subdir, kwargs)
        self.packages = packages
        self.libs_dependencies = []
#        if 'depends' in kwargs:
#             deps=_listify(kwargs['depends'])
#             for dep in deps:
#                 if isinstance(dep.held_object, FpgaLibraryTarget):
#                     self.libs_dependencies.append(dep)

class GhdlSimulator():
    def analyse_source(source, work="work"):
        cmd = ["ghdl", "-a", "--work="+work, source]
        return cmd
    def elaborate_simulation(top_entity):
        cmd = ["ghdl", "-e", top_entity]
        return cmd

def _listify(obj_or_list):
    if isinstance(obj_or_list, list):
        return obj_or_list
    return [obj_or_list]

_get_simulator = {
    "GHDL":GhdlSimulator
}

class FPGAModule(ExtensionModule):

    def _simulation_analyse_source(self, state, src, dependencies,
                                   simulator, work="work"):
        target_kwargs = {}
        target_kwargs['output'] = "analysis_"+'_'.join(src.split('/'))
        target_kwargs['depends'] = dependencies
        target_kwargs['command'] = simulator.analyse_source(
            os.path.join(state.build_to_src, state.subdir, src), work)
        target = AnalysisTarget('_'.join(src.split('/'))+"_analysis", state.subdir, target_kwargs)
        return target

    def _simulation_analyse_lib(self, state, lib, simulator):
        packages = []
        targets = []
        self_deps = []
        lib.packages = _listify(lib.packages)
        deps = _listify(lib.libs_dependencies)
        deps = [dep.held_object for dep in deps]
        for dep in deps:
            if isinstance(dep, FpgaLibraryTarget):
                dep_targets, dep_packages = self._simulation_analyse_lib(state, dep, simulator)
                self_deps += dep_targets
                targets += dep_packages
        for package in lib.packages:
            target = self._simulation_analyse_source(state, package, self_deps, simulator, lib.name)
            packages.append(target)
        for src in lib.sources:
            target = self._simulation_analyse_source(state, src, packages, simulator, lib.name)
            targets.append(target)
        return targets, packages

    @permittedKwargs({'simulator', 'args', 'sources', 'depends'})
    def simulation(self, state, args, kwargs):
        top = args[0]
        sources = []
        for src in args[1:]:
            sources.append(src)
        if kwargs.get('sources'):
            sources += kwargs['sources']
        analysis_targets = []
        libs_targets = []
        simulator = _get_simulator[kwargs["simulator"]]
        if kwargs.get('depends'):
            deps = _listify(kwargs['depends'])
            deps = [dep.held_object for dep in deps]
            for dep in deps:
                if isinstance(dep, FpgaLibraryTarget):
                    dep_targets, dep_packages = self._simulation_analyse_lib(
                        state, dep, simulator)
                    libs_targets += dep_targets
                    analysis_targets += dep_packages
        for src in sources:
            analysis_targets.append(
                self._simulation_analyse_source(state, src, libs_targets, simulator))
        target_kwargs = {}
        target_kwargs['output'] = top
        target_kwargs['command'] = simulator.elaborate_simulation(top)
        target_kwargs['depends'] = analysis_targets
        target = SimulationTarget("simulation", state.subdir, target_kwargs)
        rv = ModuleReturnValue(target, [target]+analysis_targets+libs_targets)
        return rv

    @permittedKwargs({'packages', 'sources', 'depends'})
    def library(self, state, args, kwargs):
        kwargs_lib = {}
        if 'depends' in kwargs:
            kwargs_lib['depends'] = kwargs['depends']
        kwargs_lib['input'] = kwargs['sources']
        kwargs_lib['output'] = 'dummy-'+args[0]
        kwargs_lib['command'] = ['echo', 'dummy target']
        lib = FpgaLibraryTarget(args[0], state.subdir, kwargs['packages'], kwargs_lib)
        rv = ModuleReturnValue(lib, [lib])
        return rv

    @permittedKwargs({'device', 'toolchain', 'depends', 'constraints', 'dependencies',
                      'synth_options', 'map_options', 'pr_options'})
    def bitstream(self, state, args, kwargs):
        target_kwargs = {}
        target_kwargs['output'] = 'blah'
        target_kwargs['command'] = 'echo'
        target = BitstreamTarget("bitsream", state.subdir, target_kwargs)
        rv = ModuleReturnValue(target, [target])
        return rv

def initialize():
    return FPGAModule()
