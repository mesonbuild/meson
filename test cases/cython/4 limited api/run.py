# This is taken from Cython's limited API tests and
# as a result is under Apache 2.0

import limited

limited.fib(11)

assert limited.lsum(list(range(10))) == 90
assert limited.lsum(tuple(range(10))) == 90
assert limited.lsum(iter(range(10))) == 45

try:
    limited.raises()
except RuntimeError:
    pass

limited.C()
limited.D()
limited.E()

assert limited.decode(b'a', bytearray(b'b')) == "ab"

assert limited.cast_float(1) == 1.0
assert limited.cast_float("2.0") == 2.0
assert limited.cast_float(bytearray(b"3")) == 3.0
