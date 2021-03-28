project('C++-CUDA multi-std', 'cpp', 'cuda', version : '1.0.0', default_options : ['cpp_std=c++17', 'cuda_std=c++14'])

exe = executable('prog', 'main.cu')
test('cudatest', exe)
