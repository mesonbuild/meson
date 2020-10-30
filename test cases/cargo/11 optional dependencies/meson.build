project('cargo dependencies', 'rust')

rust = import('unstable-rust')
sub1 = rust.subproject('sub1', features : ['needs_to_be_on'])

exe = executable('exe', 'exe.rs', dependencies : sub1.get_variable('dep'))

test('nested dependencies', exe)
