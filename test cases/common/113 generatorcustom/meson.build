project('generatorcustom', 'c')

gen2 = find_program('gen2.py')

res4 = configure_file(input : 'res4.txt.in',
  output : 'res4.txt',
  configuration : configuration_data())

subdir('generator')
subdir('files')
subdir('customtarget')

executable('proggie', 'main.c', allinone)
