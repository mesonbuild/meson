project('object generator', 'c')

python = find_program('python3')

# Note that this will not add a dependency to the compiler executable.
# Code will not be rebuilt if it changes.
comp = '@0@/@1@'.format(meson.current_source_dir(), 'obj_generator.py')

# Generate a header file that needs to be included.
gen = generator(python,
 output : '@BASENAME@.o',
 arguments : [comp, '@INPUT@', '@OUTPUT@'])

generated = gen.process('source.c')

e = executable('prog', 'prog.c', generated)

test('objgen', e)