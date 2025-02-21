project('my project', 'cython', 'cpp',
  default_options : ['buildtype=release'])

py = import('python').find_installation(pure: false)

py.extension_module(
    'foo',
    'foo_cpp.pyx',
    override_options : ['cython_language=cpp'],
)

