project('call swift from cpp', 'swift', 'cpp')

lib = shared_library('Library', 'lib.swift')
executable('program', 'main.cpp', link_with: [lib], include_directories: [lib.private_dir_include()])
