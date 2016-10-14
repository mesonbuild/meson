subdir('customtarget2')

catter = find_program('catter.py')

allinone = custom_target('alltogether',
    input : [res12, res3, res4, res5],
    output : 'alltogether.h',
    command : [catter, '@INPUT@', '@OUTPUT@'])
