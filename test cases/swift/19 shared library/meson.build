project('shared library', 'swift')

lib = shared_library('Library', 'lib.swift')
executable('program', 'main.swift', link_with: [lib])
