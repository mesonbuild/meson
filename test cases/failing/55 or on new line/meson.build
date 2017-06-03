project('silent_or', 'c')

if get_option('foo') == 'true' or get_option('foo') == 'auto'

else
        error('This case is fine - this error isn't triggered.')
endif

if get_option('foo') == 'true'
        or get_option('foo') == 'auto'
else
        error('This error is triggered because the or statement is silently ignored.')
endif
