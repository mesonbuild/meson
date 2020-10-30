project('cargo features', 'rust')

rust = import('unstable-rust')
dep = rust.subproject('sub1', features : ['test_feature']).get_variable('dep')

exe = executable('exe', 'exe.rs', dependencies : dep)
exe2 = executable('exe2', 'exe2.rs', dependencies : dep)

test('feature_compilation', exe)
test('default_features', exe2)
