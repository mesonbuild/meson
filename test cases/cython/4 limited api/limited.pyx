# This is taken from Cython's limited API tests and
# as a result is under Apache 2.0

import cython

@cython.binding(False)
def fib(int n):
    cdef int a, b
    a, b = 0, 1
    while b < n:
        a, b = b, a + b
    return b

def lsum(values):
    cdef long result = 0
    for value in values:
        result += value
    if type(values) is list:
        for value in reversed(<list>values):
            result += value
    elif type(values) is tuple:
        for value in reversed(<tuple>values):
            result += value
    return result

@cython.binding(False)
def raises():
    raise RuntimeError()

def decode(bytes b, bytearray ba):
    return b.decode("utf-8") + ba.decode("utf-8")

def cast_float(object o):
    return float(o)

class C:
    pass

cdef class D:
    pass

cdef class E(D):
    pass
