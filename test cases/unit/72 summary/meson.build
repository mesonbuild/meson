project('My Project', version : '1.0')

subproject('sub')
subproject('sub2', required : false)

summary({'Some boolean': false,
         'Another boolean': true,
         'Some string': 'Hello World',
         'A list': ['string', 1, true],
         'empty list': [],
        }, section: 'Configuration')
summary('A number', 1, section: 'Configuration')
summary('yes', true, bool_yn : true, section: 'Configuration')
summary('no', false, bool_yn : true, section: 'Configuration')
summary('coma list', ['a', 'b', 'c'], list_sep: ', ', section: 'Configuration')
