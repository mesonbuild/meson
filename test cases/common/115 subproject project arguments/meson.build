project('project options tester', 'c', 'cpp',
  version : '2.3.4',
  license : 'mylicense')

machine = get_option('machine')
assert(machine in ['host', 'build', 'both'])
if machine == 'host'
  native = false
elif machine == 'build'
  native = true
else
  native = 'both'
endif

if not add_languages('c', 'cpp', native : native, required : false)
  error(f'MESON_SKIP_TEST this test requires compilers for @machine@ machine(s)')
endif

add_global_arguments('-DGLOBAL_ARGUMENT', language: 'c', native : native)
add_project_arguments('-DPROJECT_OPTION', language: 'c', native : native)
add_project_arguments('-DPROJECT_OPTION_CPP', language: 'cpp', native : native)
add_project_arguments('-DPROJECT_OPTION_C_CPP', language: ['c', 'cpp'], native : native)

# XXX: when subprojects allow host/build
if machine != 'build'
  sub = subproject('subexe', version : '1.0.0')
endif

add_project_arguments('-DPROJECT_OPTION_1', language: 'c', native : native)

if machine == 'both'
  native = false
endif

e = executable('exe', 'exe.c', native : native)
e = executable('execpp', 'exe.cpp', native : native)
test('exetest', e)
test('execpptest', e)

if machine == 'both'
  e = executable('exe_build', 'exe.c', native : true)
  e = executable('execpp_build', 'exe.cpp', native : true)
  if meson.can_run_host_binaries()
    test('exetest_build', e)
    test('execpptest_build', e)
  endif
endif
