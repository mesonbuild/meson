project('vulkan test', 'c')

vulkan_dep = dependency('vulkan')

e = executable('vulkanprog', 'vulkanprog.c', dependencies : vulkan_dep)

test('vulkantest', e)
