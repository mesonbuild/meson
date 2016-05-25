project('own libc', 'c')

# A simple project that uses its own libc.

# Note that we don't need to specify anything, the flags to use
# stdlib come from the cross file.

exe = executable('selfcontained', 'prog.c')

test('standalone test', exe)
