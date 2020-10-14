project('proj1', ['c'], version : '1.0.0')

pkg = import('pkgconfig')

pkg.generate(
  name: meson.project_name(),
  description: 'Project 1',
  libraries: [],
  subdirs: [],
  version: meson.project_version(),
  filebase : meson.project_name()
)

