project('expected exitcode', 'c')

foreach num : [0,1,5,77,255]
define = '-DEXIT_CODE=' + num.to_string()
exe = executable('prog' + num.to_string(), 'failing.c', c_args: [define])
test('errorcode-'+ num.to_string(), exe, expected_exitcode: num)
endforeach
