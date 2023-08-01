libfoo2 = shared_library('foo2', 'foo2.c')

barexe = executable('bar', 'main.c',
  include_directories: incfoo,
  link_with: [libfoo, libfoo2])

# DLL in same directory does not need to be added to PATH. Make sure we can
# run bar.exe with PATH set for libfoo.dll but not libfoo2.dll.
custom_target(
  output: 'dummy',
  command: [barexe, meson.current_build_dir()],
  build_by_default: true,
)
