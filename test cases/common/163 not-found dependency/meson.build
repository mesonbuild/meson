project('dep-test')

foo_dep = dependency('', required:false)
if foo_dep.found()
  error('not-found dependency was found')
endif

bar_dep = dependency()
if bar_dep.found()
  error('not-found dependency was found')
endif
