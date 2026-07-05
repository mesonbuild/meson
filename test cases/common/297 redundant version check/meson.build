# written by Benjamin Gilbert <bgilbert@backtick.net>
project('t', 'c', meson_version: '>=0.60.0')
if meson.version().version_compare('>=0.55.0')
  v = 1
endif
if meson.version().version_compare('<0.60.0')
  v = 2
endif
# narrowing: <0.60 is indeterminate, but >=0.40 is always true within >=0.50, <0.60
if meson.version().version_compare('<99.0')
  if meson.version().version_compare('>=0.40')
    v = 3
  endif
endif

# <= vs <, should not warn
if meson.version().version_compare('<=99.0')
  if meson.version().version_compare('<99.0')
    v = 4
  endif
endif

# hide warnings about multiple args to version_compare()
if meson.version().version_compare('>1.10.0')
  if meson.version().version_compare('<99.0')
    if meson.version().version_compare('<99.0', '>=0.40')
      v = 5
    endif
    if meson.version().version_compare('>=0.40', '<99.0')
      v = 6
    endif
  endif
endif
