project('simple', ['c', 'cuda'], version : '1.0.0')

threaddep = dependency('threads')

examplelib_static = static_library(
  'example',
  files(['example_static.c']),
  dependencies : threaddep)

examplelib_shared = shared_library(
  'example',
  files(['example_shared.c']),
  soversion : meson.project_version(),
  version : meson.project_version())

exe = executable(
  'prog',
  'prog.cu',
  link_with : [
    examplelib_static,
    examplelib_shared,
  ],
  dependencies : threaddep)

test('cudatest', exe)

