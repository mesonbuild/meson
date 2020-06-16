project('clean-rpath', 'c')
subdir('unityval-dirname')
incdir = include_directories('unityval-dirname')
executable('main',
   'main.c',
   include_directories : incdir,
   link_with: unityval,
   install: true,
)
