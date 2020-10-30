project('multiple versions', 'rust')

rust = import('unstable-rust')
sub = rust.subproject('sub', version : '>= 1.5')

exe = executable('exe', 'exe.rs', dependencies : sub.get_variable('dep'))

test('test', exe)