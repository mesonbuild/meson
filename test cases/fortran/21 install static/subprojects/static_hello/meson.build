project('static-hello', 'fortran')

# staticlibsource = 'static_hello.f90'
staticlibsource = configure_file(
    command: [find_program('cp'), '@INPUT@', '@OUTPUT@'],
    input: 'static_hello.f90',
    output: 'static_hello_output.F90'
)

static_hello_lib = static_library('static_hello', staticlibsource, install: false)

static_hello_dep = declare_dependency(link_with: static_hello_lib)
