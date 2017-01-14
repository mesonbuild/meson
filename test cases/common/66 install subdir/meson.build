project('install a whole subdir', 'c')

subdir('subdir')
# A subdir with write perms only for the owner
# and read-list perms for owner and group
install_subdir('sub1', install_dir : 'share', install_mode : ['rwxr-x--t', 'root'])
install_subdir('sub/sub1', install_dir : 'share')
