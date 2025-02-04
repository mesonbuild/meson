project('required keyword in compiles functions', 'c')

cc = meson.get_compiler('c')
opt = get_option('opt')

valid = files('valid.c')
invalid = files('invalid.c')

cc.compiles(valid, name: 'valid', required : true)
cc.links(valid, name: 'valid', required : true)
if meson.can_run_host_binaries()
  cc.run(valid, name: 'valid', required : true)
endif

assert(not cc.compiles(valid, name: 'valid', required : opt))
assert(not cc.links(valid, name: 'valid', required : opt))
if meson.can_run_host_binaries()
  res = cc.run(valid, name: 'valid', required : opt)
  assert(res.compiled())
  assert(res.returncode() == 0)
  assert(res.stdout() == '')
  assert(res.stderr() == '')
endif

testcase expect_error('''compiler.compiles keyword argument 'required' was of type str but should have been one of: bool, UserFeatureOption''')
  cc.compiles(valid, name: 'valid', required : 'not a bool')
endtestcase

testcase expect_error('''Could not compile invalid''')
  cc.compiles(invalid, name: 'invalid', required : true)
endtestcase

testcase expect_error('''Could not link invalid''')
  cc.links(invalid, name: 'invalid', required : true)
endtestcase

if meson.can_run_host_binaries()
  testcase expect_error('''Could not run invalid''')
    cc.run(invalid, name: 'invalid', required : true)
  endtestcase
endif
