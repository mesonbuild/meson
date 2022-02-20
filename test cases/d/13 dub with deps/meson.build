project('dub-example', 'd')

dub_exe = find_program('dub', required : false)
if not dub_exe.found()
  error('MESON_SKIP_TEST: Dub not found')
endif

if meson.get_compiler('d').get_id() == 'gcc'
    error('MESON_SKIP_TEST: GDC cannot build vibe-d:http')
endif

vibed_deps = [
    dependency('vibe-d:http', method: 'dub')
]
if host_machine.system() == 'windows'
    vibed_deps += declare_dependency(
        link_args: [
            'user32.lib'
        ],
    )
endif


test_exe = executable('test-vibed', 'test.d', dependencies: vibed_deps)
test('test vibe-d', test_exe)
