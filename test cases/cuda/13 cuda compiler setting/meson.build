project('simple', ['cpp', 'cuda'], version : '1.0.0',
        default_options: ['cpp_std=c++2a', 'cuda_std=c++17'])

exe = executable('prog', 'prog.cu')
test('cudatest', exe)
