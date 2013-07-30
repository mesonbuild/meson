project('has member', 'c')

cc = meson.get_compiler('c')

if not cc.has_member('struct tm', 'tm_sec', prefix : '#include<time.h>')
  error('Did not detect member that exists.')
endif

if cc.has_member('struct tm', 'tm_nonexistent', prefix : '#include<time.h>')
  error('Not existing member found.')
endif
