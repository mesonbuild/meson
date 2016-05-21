project('own libc', 'c')

# A very simple libc implementation

# Start with manual flags to compile, then add platform support.

libc = static_library('c', 'libc.c', 'stubstart.s',
)

mylibc_dep = declare_dependency(link_with : libc,
  include_directories : include_directories('.')
)
