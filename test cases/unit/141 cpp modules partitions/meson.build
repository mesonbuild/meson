project('cpp modules partitions', 'cpp', default_options: {'cpp_std': 'c++latest'})

# Sources are listed so that importers come before the units they import:
# building in source order must not be enough for the build to succeed.
mod_a = static_library(
  'mod_a',
  'a/impl.cpp',
  'a/Example.Mod.ixx',
  'a/Example.Mod-Part2.ixx',
  'a/Example.Mod-Part1.ixx',
)

mod_b = static_library('mod_b', 'b/user.cpp', link_with: mod_a)

app = executable('app', 'main.cpp', link_with: [mod_b, mod_a])
test('app', app)
