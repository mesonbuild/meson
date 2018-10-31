python = import('python').find_installation('python3')

config_file = custom_target('confgen',
                            input : 'Config.java.in',
                            output : 'Config.java',
                            command : [python, '-c',
                              'import shutil; import sys; shutil.copy(sys.argv[1], sys.argv[2])',
                              '@INPUT@', '@OUTPUT@'])
