project('My Project', version : '1.0')

summary('Directories', {'bindir': get_option('bindir'),
                        'libdir': get_option('libdir'),
                        'datadir': get_option('datadir'),
                        })

subproject('sub')
subproject('sub2', required : false)

summary('Configuration', {'Some boolean': false,
                          'Another boolean': true,
                          'Some string': 'Hello World',
                          'A list': ['string', 1, true],
                          })
