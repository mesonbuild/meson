project('cargo links', 'rust', 'cpp')

rust = import('unstable-rust')

rust_exe = executable(
  'rust_main',
  'src/main.rs',
  dependencies : rust.subproject('zstd-rs').get_variable('dep')
)

cpp_exe = executable(
  'cpp_main',
  'src/main.cpp',
  dependencies : dependency('libzstd')
)

test(
  'cpp vs rust',
  find_program('test.py'),
  args : [rust_exe, cpp_exe],
)