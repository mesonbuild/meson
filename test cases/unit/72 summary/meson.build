project('My Project', version : '1.0')

subproject('sub')
subproject('sub2', required : false)

summary({'Some boolean': false,
         'Another boolean': true,
         'Some string': 'Hello World',
         'A list': ['string', 1, true],
         'empty list': [],
         'enabled_opt': get_option('enabled_opt'),
        }, section: 'Configuration')
summary({'missing prog': find_program('xyzzy', required: false),
         'existing prog': import('python').find_installation(),
         'missing dep': dependency('', required: false),
         'external dep': dependency('zlib', required: false),
         'internal dep': declare_dependency(),
        }, section: 'Stuff')
summary('A number', 1, section: 'Configuration')
summary('yes', true, bool_yn : true, section: 'Configuration')
summary('no', false, bool_yn : true, section: 'Configuration')
summary('coma list', ['a', 'b', 'c'], list_sep: ', ', section: 'Configuration')
summary('long coma list', ['alpha', 'alphacolor', 'apetag', 'audiofx', 'audioparsers', 'auparse', 'autodetect', 'avi'], list_sep: ', ', section: 'Plugins')
