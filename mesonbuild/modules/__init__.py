from .. import build
from .. import dependencies
from ..mesonlib import MesonException

_found_programs = {}

def find_program(program_name, target_name):
    if program_name in _found_programs:
        return _found_programs[program_name]
    program = dependencies.ExternalProgram(program_name)
    if not program.found():
        m = "Target {!r} can't be generated as {!r} could not be found"
        raise MesonException(m.format(target_name, program_name))
    _found_programs[program_name] = program
    return program

class GResourceTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class GResourceHeaderTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class GirTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class TypelibTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)

class VapiTarget(build.CustomTarget):
    def __init__(self, name, subdir, kwargs):
        super().__init__(name, subdir, kwargs)
