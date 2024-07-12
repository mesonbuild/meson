project('framework recasting', 'c', 'cpp')

if not find_program('cmake', required: false).found()
  error('MESON_SKIP_TEST cmake binary not available.')
endif

x = dependency('OpenAL', method: 'cmake')

y = executable('tt', files('main.cpp'), dependencies: x)
