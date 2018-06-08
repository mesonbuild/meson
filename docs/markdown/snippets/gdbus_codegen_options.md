## New options to gnome.gdbus_codegen

You can now pass additional arguments to gdbus-codegen using the `extra_args`
keyword. This is the same for the other gnome function calls.

Meson now automatically adds autocleanup support to the generated code. This
can be modified by setting the autocleanup keyword.

For example:

    sources += gnome.gdbus_codegen('com.mesonbuild.Test',
      'com.mesonbuild.Test.xml',
      autocleanup : 'none',
      extra_args : ['--pragma-once'])
