project('gl dependency with version', 'c')

host_system = host_machine.system()
if host_system not in ['linux', 'windows', 'darwin']
  error('MESON_SKIP_TEST: test only fails on Linux, Windows and OSX')
endif

# gl dependency found via system method doesn't have a meaningful version to check
dep = dependency('gl', method: 'system', version: '>0')
