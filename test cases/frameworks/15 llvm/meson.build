project('llvmtest', ['c', 'cpp'], default_options : ['c_std=c99'])

d = dependency('llvm', required : false)
if not d.found()
  error('MESON_SKIP_TEST llvm not found.')
endif

d = dependency('llvm', modules : 'not-found', required : false)
assert(d.found() == false, 'not-found llvm module found')

d = dependency('llvm', version : '<0.1', required : false)
assert(d.found() == false, 'ancient llvm module found')

d = dependency('llvm', optional_modules : 'not-found', required : false)
assert(d.found() == true, 'optional module stopped llvm from being found.')

dep_tinfo = dependency('tinfo', required : false)
if not dep_tinfo.found()
  cpp = meson.get_compiler('cpp')
  dep_tinfo = cpp.find_library('tinfo', required: false)
endif

foreach static : [true, false]
  llvm_dep = dependency(
    'llvm',
    modules : ['bitwriter', 'asmprinter', 'executionengine', 'target',
               'mcjit', 'nativecodegen'],
    required : false,
    static : static,
  )
  if llvm_dep.found()
    name = static ? 'static' : 'dynamic'
    executable(
      'sum-@0@'.format(name),
      'sum.c',
      dependencies : [
        llvm_dep, dep_tinfo,
        dependency('zlib'),
        meson.get_compiler('c').find_library('dl', required : false),
      ]
    )
  endif
endforeach
