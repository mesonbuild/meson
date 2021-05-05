project('C# MONO_PATH', 'cs')

subdir('subdir1')
subdir('subdir2')

e = executable('prog', 'prog.cs', link_with : libb)
if build_machine.system() == 'windows'
  # On windows a .config file setting developmentMode to true is needed
  configure_file(input : 'prog.exe.config', output : 'prog.exe.config', copy : true)
endif

custom_target('cs_custom', output : 'output', command : [e, '@OUTPUT@'], build_by_default : true)

test('libtest', e)
