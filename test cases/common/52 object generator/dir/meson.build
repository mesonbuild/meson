#check with a single @OUTPUT0@ in a subdirectory and multiple inputs
gen4 = generator(python,
 output : ['@BASENAME@.o'],
 arguments : [comp, cc, '@INPUT@', '@OUTPUT0@'])

generated4 = gen4.process(files('source5.c', 'source6.c'))
