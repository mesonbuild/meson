# example here is inspired by Nvidia's blog post:
#   https://developer.nvidia.com/blog/separate-compilation-linking-cuda-device-code/
# code:
#   https://docs.nvidia.com/cuda/cuda-compiler-driver-nvcc/index.html#examples

project('device linking', ['cpp'], version : '1.0.0')

# test that optional initialization of cuda works to disable thin archives
add_languages('cuda')

nvcc = meson.get_compiler('cuda')
cuda = import('unstable-cuda')

arch_flags = cuda.nvcc_arch_flags(nvcc.version(), 'Common')

message('NVCC version:   ' + nvcc.version())
message('NVCC flags:     ' + ' '.join(arch_flags))

# test device linking with -dc (which is equivalent to `--relocatable-device-code true`)
lib = static_library('devicefuncs', ['b.cu'], cuda_args : ['-dc'] + arch_flags)
exe = executable('app', 'main.cu', cuda_args : ['-dc'] + arch_flags, link_with : lib, link_args : arch_flags)

# if we don't have a CUDA-capable GPU available, avoid creating the test
if run_command('__nvcc_device_query', check : false).returncode() == 0
  test('cudatest', exe)
endif
