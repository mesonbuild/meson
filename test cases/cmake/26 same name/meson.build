# The cmMod subproject contains two files that are called `clash.c`. This broke
# earlier versions of meson, which checked whether two filenames are identical
# instead of checking whether both paths are identical.

project('same name', 'c')

cm = import('cmake')

sub_pro = cm.subproject('cmMod')

sub_exe = sub_pro.target('main')

test('test1', sub_exe)
