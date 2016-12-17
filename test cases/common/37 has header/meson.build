project('has header', 'c', 'cpp')

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


  if comp.has_header('ouagadougou.h')
    error('Found non-existant header.')
  endif
endforeach
