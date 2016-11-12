project('has header', 'c', 'cpp')

foreach comp : [meson.get_compiler('c'), meson.get_compiler('cpp')]
  if not comp.has_header('stdio.h')
    error('Stdio missing.')
  endif

  # stdio.h doesn't actually need stdlib.h, but I don't know any headers on
  # UNIX/Linux that need other headers defined beforehand
  if not comp.has_header('stdio.h', prefix : '#include <stdlib.h>')
    error('Stdio missing.')
  endif

  # XInput.h needs windows.h included beforehand. We only do this check on MSVC
  # because MinGW often defines its own wrappers that pre-include windows.h
  if comp.get_id() == 'msvc'
    if not comp.has_header('XInput.h', prefix : '#include <windows.h>')
      error('XInput.h is missing on Windows')
    endif
    if comp.has_header('XInput.h')
      error('XInput.h needs windows.h')
    endif
  endif


  if comp.has_header('ouagadougou.h')
    error('Found non-existant header.')
  endif
endforeach
