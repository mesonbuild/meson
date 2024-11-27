project('dependency-link-test', ['c', 'vala'], version: '0.1')

valac = meson.get_compiler('vala')
gee_dep = dependency('gee-0.8', required : false)

code = '''void main() {
  var a=new Gee.ArrayList<int> ();
  a.add (42);
  stdout.printf("%i",a[0]);}'''

if gee_dep.found()
  # test 1; code should link
  code_links = valac.links(
    code,
    dependencies : [gee_dep],
    name: 'links with gee-0.8 library? == YES',
  )
  assert (code_links, 'gee-0.8 library should link successfully.')
endif

# test 2; code should not link
code_links = valac.links(
  code,
  name: 'links with gee library? == NO',
)
assert (not code_links, 'gee-0.8 library should not link successfully.')

math_dep = meson.get_compiler('c').find_library('m', required : false)
glib_dep = dependency('glib-2.0', required : false)

code = '''void main() {
  var a=GLib.Math.cos (GLib.Math.PI / 3);
  stdout.printf("%f",a);}'''

if math_dep.found() and glib_dep.found()
  # test 3; code should link
  code_links = valac.links(
    code,
    dependencies : [math_dep, glib_dep],
    name: 'links with math & glib-2.0 library? == YES',
  )
  assert (code_links, 'Math library and glib-2.0 library should link successfully.')
endif

gio_dep = dependency('gio-2.0', required : false)

code = '''void main() {var s = new GLib.Settings ("test");}'''

if gio_dep.found()
  # test 4; code should link
  code_links = valac.links(
    code,
    dependencies : [gio_dep],
    name: 'links with gio-2.0? == YES',
  )
  assert (code_links, 'gio-2.0 library should link successfully.')
endif

# test 5; code should not link
  code_links = valac.links(
    code,
    name: 'links with gio-2.0? == NO',
)
assert (not code_links, 'gio-2.0 library should not link successfully.')
