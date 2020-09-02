project('cudamodule', 'cuda', version : '1.0.0')

nvcc = meson.get_compiler('cuda')
cuda = import('unstable-cuda')

arch_flags     = cuda.nvcc_arch_flags(nvcc, 'Auto', detected: ['6.0'])
arch_readable  = cuda.nvcc_arch_readable(nvcc, 'Auto', detected: ['6.0'])
driver_version = cuda.min_driver_version(nvcc)

message('NVCC version:   ' + nvcc.version())
message('NVCC flags:     ' + ' '.join(arch_flags))
message('NVCC readable:  ' + ' '.join(arch_readable))
message('Driver version: >=' + driver_version)

exe = executable('prog', 'prog.cu', cuda_args: arch_flags)
test('cudatest', exe)
