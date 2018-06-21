project('bar', 'c', license: 'Apache')

executable('bar', 'bar.c')

d = files('testdir')[0]
# Print the directory to force it to be evaluated, just in case.
message('test dir is @@0@@'.format(d))
