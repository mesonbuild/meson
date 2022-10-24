project('preprocess', 'c')

cc = meson.get_compiler('c')

add_project_arguments(['-DFOO=0', '-DBAR=0'], language: 'c')

pp_files = cc.preprocess('foo.c', 'bar.c', output: '@PLAINNAME@')

foreach f : pp_files
  message(f.full_path())
endforeach

subdir('src')

test('test-foo', executable('app', pp_files, link_depends: file_map))
