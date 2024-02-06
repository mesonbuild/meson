project('subproject dependency for build and host', 'c',
        version : '1.0')

gadget_dep = dependency('gadget',
                        default_options : ['limit=42'])
gadget_dep_native = dependency('gadget',
                               default_options : ['limit=1337'],
                               native : true)

executable('demo-native', 'main.c',
           dependencies : gadget_dep_native,
           native : true)
executable('demo', 'main.c',
            dependencies : gadget_dep,
            install : true)
