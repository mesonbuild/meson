project(
  'call swift from cpp',
  ['swift', 'cpp'],
  # Swift headers contain noexcept, which was introduced in C++11
  default_options: 'cpp_std=c++11',
)

swiftc = meson.get_compiler('swift')

# Testing C++ and Swift interoperability requires Swift 5.9
if not swiftc.version().version_compare('>= 5.9')
  error('MESON_SKIP_TEST Test requires Swift 5.9')
endif

lib = shared_library('Library', 'lib.swift')
executable('program', 'main.cpp', link_with: [lib], include_directories: [lib.private_dir_include()], swift_interoperability_mode: 'cpp')
