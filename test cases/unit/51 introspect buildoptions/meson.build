project('introspect buildargs', ['c'], default_options: ['c_std=c11', 'cpp_std=c++14', 'buildtype=release'])

subA = subproject('projectA')

r = run_command(find_program('c_compiler.py'))
if r.returncode() != 0
  error('FAILED')
endif

add_languages(r.stdout().strip(), required: true)
add_languages('afgggergearvearghergervergreaergaergasv', required: false)
