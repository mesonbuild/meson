project('install build by default target', 'c')

py3_mod = import('python3')
py3 = py3_mod.find_python()
checkexists = files('checkexists.py')

hello = executable('hello', 'hello.c',
    build_by_default : false,
    install : true
)

hello_output = join_paths(meson.build_root(), 'hello')

if host_machine.system() == 'windows'
  hello_output += '.exe'
endif

test('check-build-by-default', py3,
    args : [checkexists, '--not', hello_output])
