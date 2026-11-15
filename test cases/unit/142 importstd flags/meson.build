project('importstd flags', 'cpp',
  default_options: {'cpp_importstd': 'true',
                    'cpp_std': 'c++latest,c++23,c++20',
                    'werror': true})

# The standard library module has to be built with the arguments of the targets
# which import it, otherwise the compiler reports an incompatible environment.
# a and c share a module, b needs another one.
a = executable('a', 'a.cpp')
b = executable('b', 'b.cpp', override_options: ['b_vscrt=mt'])
c = executable('c', 'c.cpp')

test('a', a)
test('b', b)
test('c', c)
