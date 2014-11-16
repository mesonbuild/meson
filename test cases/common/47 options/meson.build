project('options', 'c')

if get_option('testoption') != 'optval'
  error('Incorrect value to test option')
endif

if get_option('other_one') != false
  error('Incorrect value to boolean option.')
endif

if get_option('combo_opt') != 'combo'
  error('Incorrect value to combo option.')
endif

if get_option('includedir') != 'include'
  error('Incorrect value in builtin option.')
endif
