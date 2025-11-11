exe = executable('prog', 'prog.cc', dependencies: dependency('cuda', modules: ['cublas', 'nvidia-ml', 'cupti']))
test('cudatest', exe)
