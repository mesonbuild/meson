import os

from .. import build
from .. import dependencies
from .. import mlog
from ..mesonlib import MesonException

class permittedSnippetKwargs:

    def __init__(self, permitted):
        self.permitted = permitted

    def __call__(self, f):
        def wrapped(s, interpreter, state, args, kwargs):
            for k in kwargs:
                if k not in self.permitted:
                    mlog.warning('Passed invalid keyword argument "%s". This will become a hard error in the future.' % k)
            return f(s, interpreter, state, args, kwargs)
        return wrapped

_found_programs = {}


class ExtensionModule:
    def __init__(self):
        self.snippets = set() # List of methods that operate only on the interpreter.

    def is_snippet(self, funcname):
        return funcname in self.snippets

def find_program(program_name, target_name):
    if program_name in _found_programs:
        return _found_programs[program_name]
    program = dependencies.ExternalProgram(program_name)
    if not program.found():
        m = "Target {!r} can't be generated as {!r} could not be found"
        raise MesonException(m.format(target_name, program_name))
    _found_programs[program_name] = program
    return program


def get_include_args(include_dirs, prefix='-I'):
    '''
    Expand include arguments to refer to the source and build dirs
    by using @SOURCE_ROOT@ and @BUILD_ROOT@ for later substitution
    '''
    if not include_dirs:
        return []

    dirs_str = []
    for incdirs in include_dirs:
        if hasattr(incdirs, "held_object"):
            dirs = incdirs.held_object
        else:
            dirs = incdirs

        if isinstance(dirs, str):
            dirs_str += ['%s%s' % (prefix, dirs)]
            continue

        # Should be build.IncludeDirs object.
        basedir = dirs.get_curdir()
        for d in dirs.get_incdirs():
            expdir = os.path.join(basedir, d)
            srctreedir = os.path.join('@SOURCE_ROOT@', expdir)
            buildtreedir = os.path.join('@BUILD_ROOT@', expdir)
            dirs_str += ['%s%s' % (prefix, buildtreedir),
                         '%s%s' % (prefix, srctreedir)]
        for d in dirs.get_extra_build_dirs():
            dirs_str += ['%s%s' % (prefix, d)]

    return dirs_str

class ModuleReturnValue:
    def __init__(self, return_value, new_objects):
        self.return_value = return_value
        assert(isinstance(new_objects, list))
        self.new_objects = new_objects

class GResourceTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class GResourceHeaderTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class GirTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class TypelibTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)

class VapiTarget(build.CustomTarget):
    def __init__(self, name, subdir, subproject, kwargs):
        super().__init__(name, subdir, subproject, kwargs)
