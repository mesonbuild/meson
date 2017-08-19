# Can override executables in the cross file

The cross file can now be used for overriding the result of
`find_program`. As an example if you want to find the `objdump`
command and have the following definition in your cross file:

    [binaries]
    ...
    objdump = '/usr/bin/arm-linux-gnueabihf-objdump-6'

Then issuing the command `find_program('objdump')` will return the
version specified in the cross file. If you need the build machine's
objdump, you can specify the `native` keyword like this:

    native_objdump = find_program('objdump', native : true)
