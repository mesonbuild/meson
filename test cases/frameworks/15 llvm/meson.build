project('llvmtest', ['c', 'cpp'], default_options : ['c_std=c99'])

d = dependency('llvm', modules : 'not-found', required : false)
assert(d.found() == false, 'not-found llvm module found')

d = dependency('llvm', version : '<0.1', required : false)
assert(d.found() == false, 'ancient llvm module found')

d = dependency('llvm', optional_modules : 'not-found', required : false)
assert(d.found() == true, 'optional module stopped llvm from being found.')

foreach static : [true, false]
  llvm_dep = dependency(
    'llvm',
    modules : ['bitwriter', 'asmprinter', 'executionengine', 'target',
               'mcjit', 'nativecodegen'],
    required : true,
    static : static,
  )
  name = static ? 'static' : 'dynamic'
  executable(
    'sum-@0@'.format(name),
    'sum.c',
    dependencies : [
      llvm_dep,
      dependency('zlib'),
      dependency('glib-2.0'),
      meson.get_compiler('c').find_library('dl', required : false),
    ]
  )
endforeach
