project('foo', 'c')

symlinked_subproject = subproject('symlinked_subproject')

executable('foo',
    sources : 'main.c',
    dependencies : symlinked_subproject.get_variable('dep')
)
