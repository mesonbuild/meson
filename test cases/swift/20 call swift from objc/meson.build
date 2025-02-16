project(
  'call swift from objc',
  ['swift', 'objc'],
)

swiftc = meson.get_compiler('swift')

lib = shared_library('Library', 'lib.swift')
executable('program', 'main.m', link_with: [lib], include_directories: [lib.private_dir_include()])
