project('278 user config-tool', 'c')

config_tool = find_program('config-tool-plain.py')
config_tool_pkg = find_program('config-tool-pkg.py')

# config-tool that just accepts --cflags --libs --version
found_dep = dependency('somedep', method: config_tool)
assert(found_dep.found(), 'should find somedep')

# config-tool that has other arguments too
found_mod = dependency('somemod', method: [config_tool_pkg, '@NAME@'])
assert(found_mod.found(), 'should find somemod')

missing_mod = dependency('missing', method: [config_tool_pkg, '@NAME@'], required: false)
assert(missing_mod.found() == false, 'should not find missing module')

exe = executable('main', 'main.c', dependencies: [found_dep, found_mod])

