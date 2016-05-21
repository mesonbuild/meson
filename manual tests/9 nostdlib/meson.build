project('own libc', 'c')

# A simple project that uses its own libc.

libc_proj = subproject('mylibc')
libc_dep = libc_proj.get_variable('mylibc_dep')

exe = executable('selfcontained', 'prog.c',
  c_args : '-nostdlib',
  link_args : '-nostdlib',
  dependencies : libc_dep,
)

test('standalone test', exe)
