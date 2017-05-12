# Tests whether fortran sources files created during configuration are properly
# scanned for dependency information

project('generated', 'fortran')

conf_data = configuration_data()

sources_fortran_basenames = ['mod2', 'mod1']
preproc_sources_fortran = []
foreach fsource_basename : sources_fortran_basenames
  infilename = '@0@.fpp'.format(fsource_basename)
  outfilename = '@0@.f90'.format(fsource_basename)
  outfile = configure_file(
      input : infilename, output : outfilename, configuration : conf_data)
  preproc_sources_fortran += [outfile]
endforeach

mylib = static_library('mylib', preproc_sources_fortran)
