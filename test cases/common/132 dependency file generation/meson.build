project('dep file gen', 'c')

cc_id = meson.get_compiler('c').get_id()
if cc_id == 'intel'
  # ICC does not escape spaces in paths in the dependency file, so Ninja
  # (correctly) thinks that the rule has multiple outputs and errors out:
  # 'depfile has multiple output paths'
  error('MESON_SKIP_TEST: Skipping test with Intel compiler because it generates broken dependency files')
endif

e = executable('main file', 'main .c')
test('test it', e)
