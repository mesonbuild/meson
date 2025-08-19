project('cuda dependency', 'cpp', 'cuda')

modules = [
    'cublas',
    'nvidia-ml',
    'cupti',
    'pcsamplingutil',
    'checkpoint',
]
exe = executable('prog', 'prog.cpp', 'kernel.cu', dependencies: dependency('cuda', modules: modules), link_language: 'cpp')
test('cudatest', exe)
