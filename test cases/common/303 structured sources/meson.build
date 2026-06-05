project('structured sources', 'c')

# Every input already exists in the right place
in_place = executable(
  'in_place',
  structured_sources(
    ['main.c'],
    {'sub' : 'sub/helper.c'},
  ),
  include_directories: include_directories('include'),
)
test('in place', in_place, expected_exitcode: 42)

gen = configure_file(
  input : 'generated.c.in',
  output : 'generated.c',
  configuration : {'RETVAL' : '58'},
)
copied = executable(
  'copied',
  structured_sources(
    ['main_generated.c', gen, 'include/inc.h'],
  ),
)
test('copied', copied, expected_exitcode: 58)

# mixing structured and unstructured sources is allowed if compilations
# are issued separately.
mixed = executable(
  'mixed',
  'main_generated.c',
  structured_sources([gen]),
  include_directories: include_directories('include'),
)
test('mixed', mixed, expected_exitcode: 58)
