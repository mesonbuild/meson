project('imports')

extmod = import('external_module', dirs : [meson.project_source_root() / 'modules'])

assert(extmod.return_true(), 'external module did not function correctly.')
