# example here is inspired by Nvidia's blog post:
#   https://developer.nvidia.com/blog/separate-compilation-linking-cuda-device-code/
# code:
#   https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/index.html#examples

project('device linking', ['cpp', 'cuda'], version : '1.0.0')

nvcc = meson.get_compiler('cuda')
cuda = import('unstable-cuda')

arch_flags = cuda.nvcc_arch_flags(nvcc.version(), 'Auto', detected : ['8.0'])

message('NVCC version:   ' + nvcc.version())
message('NVCC flags:     ' + ' '.join(arch_flags))

# test device linking with -dc (which is equivalent to `--relocatable-device-code true`)
lib = static_library('devicefuncs', ['b.cu'], cuda_args : ['-dc'] + arch_flags)
exe = executable('app', 'main.cu', cuda_args : ['-dc'] + arch_flags, link_with : lib, link_args : arch_flags)
test('cudatest', exe)
