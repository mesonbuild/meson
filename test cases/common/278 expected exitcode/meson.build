project('expected exitcode', 'c')

foreach num : [0,1,5,77,99,255]
define = '-DEXIT_CODE=' + num.to_string()
exe = executable('prog' + num.to_string(), 'failing.c', c_args: [define])
test('errorcode-'+ num.to_string(), exe, expected_exitcode: num)
endforeach

exe = executable('prog-skip', 'failing.c', c_args: ['-DEXIT_CODE=77'])
test('gnu-skip-on-expected-exitcode', exe, expected_exitcode: 5)