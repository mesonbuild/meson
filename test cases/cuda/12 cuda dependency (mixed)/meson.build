project('cuda dependency', 'cpp', 'cuda')

exe = executable('prog', 'prog.cpp', 'kernel.cu', dependencies: dependency('cuda', modules: ['cublas']), link_language: 'cpp')
test('cudatest', exe)
