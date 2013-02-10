project('library versions', 'c')

lib = shared_library('somelib', 'lib.c', \
version : '1.2.3', \
soversion : '0', \
install : true)
