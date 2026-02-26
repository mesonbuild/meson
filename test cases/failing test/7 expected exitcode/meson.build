project('expected exitcode', 'c')

passing_exe = executable('passing', 'main.c', c_args: ['-DEXIT_CODE=0'])
gnu_error_exe = executable('failing', 'main.c', c_args: ['-DEXIT_CODE=99'])
test('errorcode', passing_exe, expected_exitcode: 1)
test('errorcode-gnu-error-expected-not-specified', gnu_error_exe)
test('errorcode-gnu-error-expected-specified', gnu_error_exe, expected_exitcode: 33)
