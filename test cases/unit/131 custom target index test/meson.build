# testcase by blue42u
project('test')
python3 = find_program('python3')

gen_code = '''
import sys, pathlib
pathlib.Path(sys.argv[1]).write_text("foo")
pathlib.Path(sys.argv[2]).write_text("bar")'''
foobar_txt = custom_target(command: [python3, '-c', gen_code, '@OUTPUT@'], output: ['foo.txt', 'bar.txt'])

test_code = '''
import sys, pathlib
sys.exit(0 if pathlib.Path(sys.argv[1]).read_text() == sys.argv[2] else 4)'''

test('foo.txt', python3, args: ['-c', test_code, foobar_txt[0], 'foo'])
test('bar.txt', python3, args: ['-c', test_code, foobar_txt[1], 'bar'])
