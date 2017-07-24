project('vulkan test', 'c')

sdl2_dep = dependency('vulkan')

e = executable('vulkanprog', 'vulkanprog.c', dependencies : sdl2_dep)

test('vulkantest', e)
