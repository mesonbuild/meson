project('My Project', version : '1.0')

subproject('sub')
subproject('sub2', required : false)

summary('Configuration', {'Some boolean': false,
                          'Another boolean': true,
                          'Some string': 'Hello World',
                          'A list': ['string', 1, true],
                          })
summary('Configuration', 'A number', 1)
summary('Configuration', 'yes', true, bool_yn : true)
summary('Configuration', 'no', false, bool_yn : true)
