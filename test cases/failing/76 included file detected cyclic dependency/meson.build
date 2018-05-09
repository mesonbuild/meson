# Should fail because included_file1 includes included_file2 and
# included_file2 includes included_file1

project('included file detected cyclic dependency', 'c')

include('included_file2')

