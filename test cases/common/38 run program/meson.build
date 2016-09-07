project('run command', 'c')

if build_machine.system() == 'windows'
  c = run_command('cmd', '/c', 'echo', 'hello')
else
  c = run_command('echo', 'hello')
endif

correct = 'hello'

if c.returncode() != 0
  error('Executing echo failed.')
endif

result = c.stdout().strip()

if result != correct
  error('Getting stdout failed.')
endif

if c.stderr() != ''
  error('Extra text in stderr.')
endif

# Now the same with a script.

if build_machine.system() == 'windows'
  cs = run_command('scripts/hello.bat')
else
  cs = run_command('scripts/hello.sh')
endif

if cs.returncode() != 0
  error('Executing script failed.')
endif

if cs.stdout().strip() != correct
  error('Getting stdout failed (script).')
endif

if cs.stderr() != ''
  error('Extra text in stderr (script).')
endif

# We should be able to have files() in argument
f = files('meson.build')

if build_machine.system() == 'windows'
  c = run_command('cmd', '/c', 'echo', f)
else
  c = run_command('echo', f)
endif

if c.returncode() != 0
  error('Using files() in argument failed.')
endif

