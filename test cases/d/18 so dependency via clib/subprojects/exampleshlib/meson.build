project(
  'exampleshlib',
  'c',
  meson_version : '>= 1.3.0',
  version : '0.1',
  default_options : ['warning_level=3'],
)

sources = [
  'exampleshlib.c',
]

exampleshlib = shared_library(
  'exampleshlib',
  sources,
  install : true,
)

exampleshlib_dep = declare_dependency(include_directories : include_directories('.'),
  link_with : exampleshlib)
