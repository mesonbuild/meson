project('library-path', 'c')

snippets = import('snippets')
snippets.symbol_visibility_header('config.h')

lib = shared_library('mylib', 'mylib.c',
  c_args: '-DLIBRARY_PATH_COMPILATION',
)

env = environment()
env.prepend_library_path(lib)

prog = find_program('prog.py')
custom_target(
    output: 'dummy.txt',
    command: [prog, lib],
    env: env,
    build_by_default: true,
)
