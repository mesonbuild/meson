project('use-hello-gen', 'c')

genhello = find_program(
  'gen',
  fallback: 'stuff',
  required: true,
)
greeter = custom_target(
  'greeter',
  command: [genhello, 'folks', 'hello.c'],
  output: 'hello.c',
)
hello = executable('hello', greeter)
test(
  'test-hello',
  find_program('python3'), args: [
    '-c',
    '''
import sys
import subprocess
output = subprocess.check_output(sys.argv[1])
assert output.strip() == b'hello, folks!', repr(output)
    ''',
    hello
  ]
)
