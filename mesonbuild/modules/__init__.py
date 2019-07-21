import os

from .. import build


class ExtensionModule:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.snippets = set() # List of methods that operate only on the interpreter.

    def is_snippet(self, funcname):
        return funcname in self.snippets


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
