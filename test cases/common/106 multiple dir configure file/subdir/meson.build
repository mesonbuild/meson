configure_file(input : 'someinput.in',
  output : 'outputsubdir',
  install : false,
  copy: true)

py3 = import('python').find_installation()

cfile1 = configure_file(input : 'foo.txt',
                        output : 'foo.h.in',
                        capture : true,
                        command : [py3, '-c', 'print("#mesondefine FOO_BAR")'])
