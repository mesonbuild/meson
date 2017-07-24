project('vulkan test', 'c')

vulkan_dep = dependency('vulkan')

e = executable('vulkanprog', 'vulkanprog.c', dependencies : sdl2_dep)

test('vulkantest', e)
