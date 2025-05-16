project('main in multi-file library', 'swift', 'c')

lib = static_library('Library', 'main.swift', 'more.swift', include_directories: ['.'])
executable('program', 'aux.c', link_with: [lib])
