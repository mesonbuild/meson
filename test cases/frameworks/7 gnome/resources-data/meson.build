subdir('subdir')

fake_generator_script = '''
import os, sys
assert os.path.exists(sys.argv[1]), "File %s not found" % sys.argv[1]
print("This is a generated resource.")
'''

# Generate file res3.txt from file res3.txt.in. This is then included
# in a GResource file, driven by resources/meson.build.
res3_txt = custom_target('res3',
  input: 'res3.txt.in',
  output: 'res3.txt',
  command: [py3, '-c', fake_generator_script, '@INPUT@'],
  capture: true,
)
