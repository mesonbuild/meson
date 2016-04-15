project('own libc', 'c')

# A simple project that uses its own libc.

# Start with manual flags to compile, then add platform support.

libc = static_library('c', 'libc.c', 'stubstart.s',
  c_args : '-nostdlib',
  link_args : '-nostdlib',
)

exe = executable('selfcontained', 'prog.c',
  c_args : '-nostdlib',
  link_args : '-nostdlib',
  link_with : libc,
)

test('standalone test', exe)
