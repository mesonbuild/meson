subhello = executable('subhello', sources: '../hello.c')

# All targets created in subdir/ will be in a new component called 'subcomponent'
subdir('subsubdir',
  components: [component('subsubcomponent')])
