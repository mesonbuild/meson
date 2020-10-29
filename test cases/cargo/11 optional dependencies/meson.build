project('cargo dependencies', 'rust')

rust = import('unstable-rust')
sub1 = rust.subproject('sub1')

exe = executable('exe', 'exe.rs', dependencies : sub1.get_variable('dep'))

test('nested dependencies', exe)
