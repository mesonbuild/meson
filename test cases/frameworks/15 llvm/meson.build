project('llvmtest', ['c', 'cpp'], default_options : ['c_std=c99'])

llvm_dep = dependency(
  'llvm',
  modules : ['bitwriter', 'asmprinter', 'executionengine', 'target',
             'mcjit', 'nativecodegen'],
  required : true,
)

executable('sum', 'sum.c',  dependencies : llvm_dep)
