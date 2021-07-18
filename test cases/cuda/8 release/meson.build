project('release', 'cuda', version : '1.0.0', default_options : ['buildtype=release', 'b_ndebug=if-release'])

exe = executable('prog', 'main.cu')
test('cudatest', exe)
