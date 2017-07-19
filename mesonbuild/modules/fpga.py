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
from . import noKwargs
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

class GhdlSimulator():
    def analyse_library():
        pass
    def analyse_source(source):
        cmd = ["ghdl", "-a", source]
        return cmd
    def elaborate_simulation(top_entity):
        cmd = ["ghdl", "-e", top_entity]
        return cmd

_get_simulator={
    "GHDL":GhdlSimulator
}

class FPGAModule(ExtensionModule):

    @permittedKwargs({'simulator','args','sources'})
    def simulation(self, state, args, kwargs):
        top = args[0]
        sources = []
        for src in args[1:]:
            sources.append(src)
        if kwargs.get('sources'):
            sources += kwargs['sources']
        analysis_targets = []
        simulator=_get_simulator[kwargs["simulator"]]
        for src in sources:
            target_kwargs = {}
            target_kwargs['output']="analysis_"+src
            target_kwargs['command']=simulator.analyse_source(os.path.join(state.build_to_src, state.subdir,src))
            target = AnalysisTarget(src+"_analysis", state.subdir,target_kwargs)
            analysis_targets.append(target)
        target_kwargs = {}
        target_kwargs['output']=top
        target_kwargs['command']=simulator.elaborate_simulation(top)
        target_kwargs['depends']=analysis_targets
        target = SimulationTarget("simulation", state.subdir,target_kwargs)
        rv = ModuleReturnValue(target, [target]+analysis_targets)
        return rv

    @permittedKwargs({'package','sources'})
    def library(self, state, args, kwargs):
        target_kwargs = {}
        target_kwargs['output']='blah'
        target_kwargs['command']='echo'
        target = BitstreamTarget("bitsream", state.subdir,target_kwargs)
        rv = ModuleReturnValue(target, [target])
        return rv

    @permittedKwargs({'device','toolchain','constraints','dependencies',
                     'synth_options','map_options','pr_options'})
    def bitstream(self, state, args, kwargs):
        target_kwargs = {}
        target_kwargs['output']='blah'
        target_kwargs['command']='echo'
        target = BitstreamTarget("bitsream", state.subdir,target_kwargs)
        rv = ModuleReturnValue(target, [target])
        return rv

def initialize():
    return FPGAModule()
