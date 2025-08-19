project('cuda dependency', 'cpp', 'cuda')

exe = executable('prog', 'prog.cpp', 'kernel.cu', dependencies: dependency('cuda', modules: ['cublas', 'nvidia-ml', 'cupti']), link_language: 'cpp')
test('cudatest', exe)
