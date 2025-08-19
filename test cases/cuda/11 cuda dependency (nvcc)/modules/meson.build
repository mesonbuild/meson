modules = [
    'cublas',
    'nvidia-ml',
    'cupti',
    'pcsamplingutil',
    'checkpoint',
]
exe = executable('prog', 'prog.cu', dependencies: dependency('cuda', modules: modules))
test('cudatest', exe)

if not meson.is_cross_build()
  exe = executable('prog_nvvm', 'prog_nvvm.cu', dependencies: dependency('cuda', modules: ['nvvm']))
  test('nvvmtest', exe)
endif
