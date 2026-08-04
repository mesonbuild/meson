## Remove Version Guessing for boost_python and boost_numpy

Previously if you specified `boost_python` or `boost_numpy` as modules to
`dependency('boost')` it would try to guess the version of python to use based
on the avaiable library files. This feature was ill advised and has been
removed.
