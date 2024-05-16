project('link-test', ['c', 'vala'], version: '0.1')

valac = meson.get_compiler('vala')

code = '''void main() {
  const double PI3 = 1.047197551196597746154214461093167628;
  var a = GLib.Math.cos (PI3);
  stdout.printf ("%f\n", a); }'''

# test 1; code should link
code_links = valac.links(
  code,
  args: '--Xcc=-lm',
  name: 'links with math library? == YES',
)
assert (code_links, 'Math library should link successfully.')

# test 2; code should not link
code_links = valac.links(
  code,
  args: '--Xcc=-lfake_library_90DFE450330A',
  name: 'links with fake library? == NO',
)
assert (not code_links, 'Fake library should not link successfully.')
