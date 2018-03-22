project('asan', 'cpp', default_options: 'b_sanitize=address')

if target_machine.system() == 'windows'
    error('MESON_SKIP_TEST address sanitizing not supported on windows, libasan not available')
endif

lib = shared_library('my_lib', 'lib.cpp')

test('asan', executable('asan', 'main.cpp', link_with: lib))
