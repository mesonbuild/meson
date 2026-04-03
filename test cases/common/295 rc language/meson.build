project('rc language', 'c')

if not add_languages('rc', required: false, native: false)
  error('MESON_SKIP_TEST: rc compiler not found')
endif

# Test add_project_arguments with rc language
add_project_arguments('-DPROJECT_DEF', language: 'rc', native: false)

# Test that .rc files work directly as sources in static_library
lib = static_library('rclib', 'resource.rc')

# Test rc_args on a target
lib2 = static_library('rclib2', 'resource.rc',
  rc_args : ['-DLIB_BUILD'])
