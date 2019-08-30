project('benchmark', 'c')

delayer = executable('delayer', 'delayer.c', c_args : '-D_GNU_SOURCE', build_by_default : false)
benchmark('delayer', delayer)
