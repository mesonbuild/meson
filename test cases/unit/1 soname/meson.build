project('vertest', 'c')

shared_library('nover', 'versioned.c',
 install : true)

shared_library('verset', 'versioned.c',
 install : true,
 version : '4.5.6')

shared_library('soverset', 'versioned.c',
 install : true,
 soversion : '1.2.3')

shared_library('bothset', 'versioned.c',
 install : true,
 soversion : '1.2.3',
 version : '4.5.6')

shared_library('settosame', 'versioned.c',
  install : true,
  soversion : '7.8.9',
  version : '7.8.9')
