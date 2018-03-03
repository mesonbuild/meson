project('100 print null')

find_file_list = run_command(find_program('find'), '-type', 'f', '-print0')
assert(find_file_list.returncode() == 0, 'Didn\'t find any files.')

found_files = []
foreach l : find_file_list.stdout().split('\0')
	found_files += [files([l])]
endforeach
