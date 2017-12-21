win = import('windows')

rc_writer = find_program('./gen-res.py')

rc_target = custom_target('RC source file',
    input : 'myres.rc.in',
    output : 'myres.rc',
    command : [rc_writer, '@INPUT@', '@OUTPUT@', files('sample.ico')],
    install : false,
    build_always : true)

res = win.compile_resources(rc_target,
  include_directories : inc)
