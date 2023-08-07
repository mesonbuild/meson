subdirfiles = files('subdirfile.txt')
assert(fs.exists('subdirfile.txt'), 'Subdir file lookup is broken.')
assert(fs.is_samepath(meson.project_source_root(), '..'), 'is_samepath not detecting same directory')
assert(fs.is_samepath(meson.project_build_root(), meson.current_build_dir() / '..'), 'is_samepath not detecting same directory')

assert(fs.is_samepath(subdirfiles[0], 'subdirfile.txt'), 'is_samepath not detecting same directory when using File and str')

# More relative_to to test subdir/builddir components

python3 = find_program('python3')
build_to_src = fs.relative_to(meson.current_source_dir(), meson.current_build_dir())
src_to_build = fs.relative_to(meson.current_build_dir(), meson.current_source_dir())

btgt = executable('btgt', 'btgt.c')
ctgt = custom_target(
  'copied-files',
  command: [
    python3,
    '-c',
    'import shutil; shutil.copyfile("@INPUT0@", "@OUTPUT0@"); shutil.copyfile("@INPUT1@", "@OUTPUT1@")'
  ],
  input: [
    'subdirfile.txt',
    'meson.build',
  ],
  output: [
    'subdirfile.txt',
    'meson.build',
  ],
)

if build_machine.system() == 'windows'
  # Test that CustomTarget works
  assert(fs.relative_to('subdirfile.txt', ctgt) == '..\\@0@\\subdirfile.txt'.format(build_to_src))
  assert(fs.relative_to(ctgt, 'subdirfile.txt') == '..\\@0@\\subdirfile.txt'.format(src_to_build))
  # Test that CustomTargetIndex works
  assert(fs.relative_to('meson.build', ctgt[1]) == '..\\@0@\\meson.build'.format(build_to_src))
  assert(fs.relative_to(ctgt[1], 'meson.build') == '..\\@0@\\meson.build'.format(src_to_build))
  # Test that BuildTarget works
  assert(fs.relative_to('subdirfile.txt', btgt) == '..\\@0@\\subdirfile.txt'.format(build_to_src))
  assert(fs.relative_to(btgt, 'subdirfile.txt') == '..\\@0@\\btgt.exe'.format(src_to_build))
else
  # Test that CustomTarget works
  assert(fs.relative_to('subdirfile.txt', ctgt) == '../@0@/subdirfile.txt'.format(build_to_src))
  assert(fs.relative_to(ctgt, 'subdirfile.txt') == '../@0@/subdirfile.txt'.format(src_to_build))
  # Test that CustomTargetIndex works
  assert(fs.relative_to('meson.build', ctgt[1]) == '../@0@/meson.build'.format(build_to_src))
  assert(fs.relative_to(ctgt[1], 'meson.build') == '../@0@/meson.build'.format(src_to_build))
  # Test that BuildTarget works
  assert(fs.relative_to('subdirfile.txt', btgt) == '../@0@/subdirfile.txt'.format(build_to_src))
  if host_machine.system() == 'windows'
    assert(fs.relative_to(btgt, 'subdirfile.txt') == '../@0@/btgt.exe'.format(src_to_build))
  else
    assert(fs.relative_to(btgt, 'subdirfile.txt') == '../@0@/btgt'.format(src_to_build))
  endif
endif
