
project('run command with cwd', 'c')

# Testing file path formats
test_setup = run_command('mkdir', ['target_cwd'])
run_command('touch', ['touch1.txt'], cwd: 'target_cwd')
run_command('touch', ['touch2.txt'], cwd: './target_cwd')
run_command('touch', ['touch3.txt'], cwd: 'target_cwd/')
run_command('touch', ['touch_w_meson.txt'], cwd: meson.source_root() + '/target_cwd')

