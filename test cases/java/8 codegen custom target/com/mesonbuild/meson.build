python = import('python').find_installation('python3')

config_file = custom_target('confgen',
                            input : 'Config.java.in',
                            output : 'Config.java',
                            command : [python, '-c',
                              'import shutil, sys, time; time.sleep(1); shutil.copy(sys.argv[1], sys.argv[2])',
                              '@INPUT@', '@OUTPUT@'])
