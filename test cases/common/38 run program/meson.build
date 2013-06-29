project('run command', 'c')

c = run_command('echo', 'hello')
correct = 'hello'

if c.returncode() != 0
  error('Executing echo failed.')
endif

result = c.stdout()
result = result.strip()

if result != correct
  error('Getting stdout failed.')
endif

if c.stderr() != ''
  error('Extra text in stderr.')
endif
