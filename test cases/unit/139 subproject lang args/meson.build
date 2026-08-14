project('top', 'c')

subproject('sub')

static_library('top', 'top.c')
static_library('over', 'over.c', override_options: ['c_args=-DOVERRIDE_FLAG'])
