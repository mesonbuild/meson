# Tests whether fortran sources files created during configuration are properly
# scanned for dependency information

project('generated', 'fortran')

conf_data = configuration_data()
conf_data.set('ONE', 1)
conf_data.set('TWO', 2)

templates_basenames = ['mod2', 'mod1']
generated_sources = []
foreach template_basename : templates_basenames
  infilename = '@0@.fpp'.format(template_basename)
  outfilename = '@0@.f90'.format(template_basename)
  outfile = configure_file(
      input : infilename, output : outfilename, configuration : conf_data)
  generated_sources += [outfile]
endforeach

sources = ['prog.f90'] + generated_sources
exe = executable('generated', sources)
test('generated', exe)
