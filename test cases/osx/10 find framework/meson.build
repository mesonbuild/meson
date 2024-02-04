project('find_framework test', 'objc')

objcc = meson.get_compiler('objc')

cf_dep = objcc.find_framework('CoreFoundation', dirs: ['/System/Library/Frameworks'])

executable('find_framework_tester',
  'main.m',
  dependencies: [cf_dep],
)
