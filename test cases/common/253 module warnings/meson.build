project('module warnings', meson_version : '>= 0.56')

import('python3')          # deprecated module
import('java')             # new module
import('unstable-keyval')  # module that has been stabilized, import with unstable-

ice = import('icestorm', required : false)
assert(not ice.found(), 'unstable-icestorm module should not be importable as `simd`')
