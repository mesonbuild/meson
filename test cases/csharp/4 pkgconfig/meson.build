project('C# pkg-config', 'cs')

nunit_dep = dependency('nunit')
nunit_runner = find_program('nunit-console')

test_lib = library('test_lib', 'test-lib.cs', dependencies: nunit_dep)
test('nunit test', nunit_runner, args: test_lib)
