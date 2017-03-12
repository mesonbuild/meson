project('has header', 'c', 'cpp')

host_system = host_machine.system()

non_existant_header = 'ouagadougou.h'

# Copy it into the builddir to ensure that it isn't found even if it's there
configure_file(input : non_existant_header,
  output : non_existant_header,
  configuration : configuration_data())

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  if not comp.has_header('stdio.h')
    error('Stdio missing.')
  endif

  # stdio.h doesn't actually need stdlib.h, but just test that setting the
  # prefix does not result in an error.
  if not comp.has_header('stdio.h', prefix : '#include <stdlib.h>')
    error('Stdio missing.')
  endif

  # XInput.h should not require type definitions from windows.h, but it does
  # require macro definitions. Specifically, it requires an arch setting for
  # VS2015 at least.
  # We only do this check on MSVC because MinGW often defines its own wrappers
  # that pre-include windows.h
  if comp.get_id() == 'msvc'
    if not comp.has_header('XInput.h', prefix : '#include <windows.h>')
      error('XInput.h should not be missing on Windows')
    endif
    if not comp.has_header('XInput.h', prefix : '#define _X86_')
      error('XInput.h should not need windows.h')
    endif
  endif

  # Test that the following GCC bug doesn't happen:
  # https://gcc.gnu.org/bugzilla/show_bug.cgi?id=80005
  # https://github.com/mesonbuild/meson/issues/1458
  if host_system == 'linux'
    assert(comp.has_header('linux/if.h'), 'Could not find <linux/if.h>')
  endif

  # This header exists in the source and the builddir, but we still must not
  # find it since we are looking in the system directories.
  assert(not comp.has_header(non_existant_header), 'Found non-existant header.')
endforeach
