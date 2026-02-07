project('pcre2', 'c')

pcre2_lib = shared_library('pcre2', 'pcre.c')

pcre2_dep = declare_dependency(link_with: pcre2_lib)

meson.override_dependency('pcre2', pcre2_dep)
