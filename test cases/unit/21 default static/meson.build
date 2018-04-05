project('default-static', 'c')

sdk_dep = dependency('sdk')
platform_dep = dependency('platform')

app = executable('app', 'main.c', dependencies : [sdk_dep, platform_dep])

test('default-static', app)
