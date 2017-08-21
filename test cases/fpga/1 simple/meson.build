project('lattice', 'c')

yosys_bin = find_program('yosys')
arachne_bin = find_program('arachne-pnr')
icepack_bin = find_program('icepack')
iceprog_bin = find_program('iceprog')
icetime_bin = find_program('icetime')

pcffile = files('spin.pcf')

blif = custom_target('spin_blif',
  input : 'spin.v',
  output : 'spin.blif',
  command : [yosys_bin, '-q', '-p', 'synth_ice40 -blif @OUTPUT@', '@INPUT@'],
  )

asc = custom_target('spin_asc',
  input : blif,
  output : 'spin.asc',
  command : [arachne_bin, '-q', '-d', '1k', '-p', pcffile, '@INPUT@', '-o', '@OUTPUT@'],
  )

bin = custom_target('spin-bin',
  input : asc,
  output : 'spin.bin',
  command : [icepack_bin, '@INPUT@', '@OUTPUT@'],
  build_by_default : true
  )

run_target('spin-time',
  command : [icetime_bin, '-tmd', 'hx1k', asc],
  )

run_target('spin-upload',
  command : [iceprog_bin, bin]
  )
