project('check header', 'c', 'cpp')

host_system = host_machine.system()

# Configure file to place the output file in the build dir.
configure_file(
    input: 'config.h.in',
    output: 'config.h',
    configuration: configuration_data({'MACRO': true}))

fallback = ''

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  assert(comp.check_header('stdio.h', prefix : fallback), 'Stdio missing.')

  # stdio.h doesn't actually need stdlib.h, but just test that setting the
  # prefix does not result in an error.
  assert(comp.check_header('stdio.h', prefix : '#include <stdlib.h>' + fallback),
         'Stdio missing.')

  # Test that check_header behaves differently than has_header. The second
  # check without windows.h will fail with check_header.
  # We only do this check on MSVC because MinGW often defines its own wrappers
  # that pre-include windows.h
  if comp.get_id() == 'msvc'
    assert(comp.check_header('XInput.h', prefix : '#include <windows.h>' + fallback),
           'XInput.h should not be missing on Windows')
    assert(not comp.check_header('XInput.h'), 'XInput.h needs windows.h')
  endif

  # Test that the following GCC bug doesn't happen:
  # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=80005
  # https://github.com/mesonbuild/meson/issues/1458
  if host_system == 'linux'
    assert(comp.check_header('linux/socket.h', prefix : fallback),
           'Could not find <linux/socket.h>')
    if comp.has_header('intrin.h', prefix : fallback)
      assert(not comp.check_header('intrin.h'),
             'intrin.h should not be usable on linux')
    endif
  endif

  # The header was created in the build dir via configure_file and should be found
  # even if the build dir is not manually added.
  assert(comp.check_header('header.h', include_directories: include_directories('.')),
          'configured header in build dir not found')
endforeach
