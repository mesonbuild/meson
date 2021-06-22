project('llvmtest', ['c', 'cpp'], default_options : ['c_std=c99'])

method = get_option('method')
static = get_option('link-static')
d = dependency('llvm', required : false, method : method, static : static)
if not d.found()
  error('MESON_SKIP_TEST llvm not found.')
endif

d = dependency('llvm', modules : 'not-found', required : false, static : static, method : method)
assert(d.found() == false, 'not-found llvm module found')

d = dependency('llvm', version : '<0.1', required : false, static : static, method : method)
assert(d.found() == false, 'ancient llvm module found')

d = dependency('llvm', optional_modules : 'not-found', required : false, static : static, method : method)
assert(d.found() == true, 'optional module stopped llvm from being found.')

# Check we can apply a version constraint
d = dependency('llvm', version : ['< 500', '>=@0@'.format(d.version())], required: false, static : static, method : method)
assert(d.found() == true, 'Cannot set version constraints')

dep_tinfo = dependency('tinfo', required : false)
if not dep_tinfo.found()
  cpp = meson.get_compiler('cpp')
  dep_tinfo = cpp.find_library('tinfo', required: false)
endif

llvm_dep = dependency(
  'llvm',
  modules : ['bitwriter', 'asmprinter', 'executionengine', 'target',
             'mcjit', 'nativecodegen', 'amdgpu'],
  required : false,
  static : static,
  method : method,
)

if not llvm_dep.found()
  error('MESON_SKIP_TEST required llvm modules not found.')
endif

executable(
    'sum',
    'sum.c',
    dependencies : [
      llvm_dep, dep_tinfo,
      # zlib will be statically linked on windows
      dependency('zlib', required : host_machine.system() != 'windows'),
      meson.get_compiler('c').find_library('dl', required : false),
    ]
  )
