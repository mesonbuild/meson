import os
from types import MethodType

def _add_funcs(self):
    self.funcs['glib_compile_resources'] = MethodType(compile_resources, self)

def compile_resources(self, node, args, kwargs):
    source_dir = os.path.join(self.environment.get_source_dir(), self.subdir)
    src_dir = kwargs.pop('src_dir', None)
    if isinstance(src_dir, str):
        source_dir = os.path.join(source_dir, src_dir)
    c_name = kwargs.pop('c_name', None)
    if c_name and not isinstance(c_name, str):
        raise InterpreterException('Keyword argument must be a string.')
    name = 'glib-compile-resources'
    progobj = self.func_find_program(self, [name], {'required' : True})
    kwargs.setdefault('build_always', True)
    kwargs['command'] = [progobj, '@INPUT0@', '--generate', '--sourcedir', source_dir, '--target', '@OUTPUT0@']
    if c_name:
        kwargs['command'] += ['--c-name', c_name]
    kwargs['input'] = args[1]
    kwargs['output'] = args[0] + '.c'
    resource_c = self.func_custom_target(node, [kwargs['output']], kwargs)
    kwargs['output'] = args[0] + '.h'
    resource_h = self.func_custom_target(node, [kwargs['output']], kwargs)
    return [resource_c, resource_h]
