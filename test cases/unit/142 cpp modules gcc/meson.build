project('cpp modules gcc', 'cpp', default_options: {'cpp_std': 'c++20'})

# GCC does not recognize the .ixx and .cppm extensions, all module units are
# plain .cpp files. Importers are listed before the units they import.
mod_a = static_library(
  'mod_a',
  'a/impl.cpp',
  'a/mod.cpp',
  'a/mod-part1.cpp',
  cpp_args: '-fmodules-ts',
)

mod_b = static_library('mod_b', 'b/user.cpp', link_with: mod_a, cpp_args: '-fmodules-ts')

app = executable('app', 'main.cpp', link_with: [mod_b, mod_a])
test('app', app)
