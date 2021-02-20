project('rust linking to c using dependency', 'c', 'rust')

if host_machine.system() == 'darwin'
  error('MESON_SKIP_TEST: doesnt work right on macos, please fix!')
endif

dep_zlib = dependency('zlib')

l = static_library(
        'c_accessing_zlib',
        'c_accessing_zlib.c',
        dependencies: [dep_zlib],
    )

e = executable(
        'prog', 'prog.rs',
        link_with : l,

        # This rust_args allows the link to succeed
        # rust_args: ['-l', 'static=z'],
    )

test('cdepstest', e)
