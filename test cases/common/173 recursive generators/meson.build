project('recursive generator', 'cpp')

stripdoc = find_program('stripdoc.py')

genjson = generator(stripdoc,
  output : '@BASENAME@.json',
  arguments : ['@INPUT@', '@BUILD_DIR@'])

gensrc = find_program('gensrc.py')

gensrc_gen = generator(gensrc,
  output : '@BASENAME@.cpp',
  arguments : ['@INPUT@', '@BUILD_DIR@'])

json = genjson.process('source.dat')

generated = gensrc_gen.process(json)

exe = executable('prog', generated)

test('generated test', exe)
