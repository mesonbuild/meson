project('zigtest-deps', 'zig')

curl_dep = dependency('libcurl')

executable(
  'zigtest-deps',
  'src/main.zig',
  zig_args : '-lc', # XXX: I don't like this solution at all.
  link_args : '-lc',
  dependencies : curl_dep,
)
