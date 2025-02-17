project('main in single-file library', 'swift', 'c')

lib = static_library('Library', 'main.swift', include_directories: ['.'])
executable('program', 'program.c', link_with: [lib])
