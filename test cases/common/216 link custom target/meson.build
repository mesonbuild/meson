project('link_with_custom_target', 'c')

lib = build_target('mylib', 'libfile.c', 'libfile2.c', 'libfile3.c', 'libfile4.c', target_type : 'static_library')

# Faking custom_target build
lib_name = 'libmycustomlib.a'
lib_custom = custom_target('gen_lib',
                           depends: lib,
                           command: [find_program('copylib.py'), lib.full_path(), '@OUTDIR@'/lib_name],
                           output: lib_name)

exe = executable('prog', 'main.c', link_with : lib_custom)
