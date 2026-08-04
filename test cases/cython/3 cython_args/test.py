import cythonargs
import builtincythonargs

assert cythonargs.test() == 1
assert builtincythonargs.test() == 1
