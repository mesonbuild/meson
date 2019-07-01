project('llvmtest', ['c', 'cpp'], default_options : ['c_std=c99'])

d = dependency('llvm', required : false, method : 'config-tool')
if not d.found()
  d = dependency('llvm', required : false, static : true)
  if not d.found()
    error('MESON_SKIP_TEST llvm not found.')
  else
    static = true
  endif
else
  static = false
endif

d = dependency('llvm', modules : 'not-found', required : false, static : static)
assert(d.found() == false, 'not-found llvm module found')

d = dependency('llvm', version : '<0.1', required : false, static : static)
assert(d.found() == false, 'ancient llvm module found')

d = dependency('llvm', optional_modules : 'not-found', required : false, static : static)
assert(d.found() == true, 'optional module stopped llvm from being found.')

# Check we can apply a version constraint
d = dependency('llvm', version : ['< 500', '>=@0@'.format(d.version())], required: false, static : static)
assert(d.found() == true, 'Cannot set version constraints')

dep_tinfo = dependency('tinfo', required : false)
if not dep_tinfo.found()
  cpp = meson.get_compiler('cpp')
  dep_tinfo = cpp.find_library('tinfo', required: false)
endif

foreach method : ['config-tool', 'cmake']
  foreach static : [true, false]
    message('Trying method @0@ for @1@ link'.format(method, static ? 'static' : 'dynamic'))
    llvm_dep = dependency(
      'llvm',
      modules : ['bitwriter', 'asmprinter', 'executionengine', 'target',
                'mcjit', 'nativecodegen', 'amdgpu'],
      required : false,
      static : static,
      method : method,
    )
    if llvm_dep.found()
      name = static ? 'static' : 'dynamic'
      executable(
        'sum-@0@-@1@'.format(name, method),
        'sum.c',
        dependencies : [
          llvm_dep, dep_tinfo,
          # zlib will be statically linked on windows
          dependency('zlib', required : host_machine.system() != 'windows'),
          meson.get_compiler('c').find_library('dl', required : false),
        ]
      )
    endif
  endforeach
endforeach
