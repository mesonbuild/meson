project('main in multi-file library', 'swift', 'c')

lib = static_library('Library', 'main.swift', 'more.swift', include_directories: ['.'])
executable('program', 'program.c', link_with: [lib])
