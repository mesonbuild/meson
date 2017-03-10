project('option override', 'c',
  default_options : 'unity=true')

executable('mustunity', 'one.c', 'two.c')
executable('notunity', 'three.c', 'four.c',
  override_options : ['unity=false'])
