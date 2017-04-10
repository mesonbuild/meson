project('call-found-on-required-dep', 'c')

dep_thr = dependency('zlib')
if dep_thr.found()
    message('found zlib, which is actually bad')
endif
