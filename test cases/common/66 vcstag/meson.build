project('vcstag', 'c')

version_src = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag.c',
fallback : '1.0.0')

version_src_disabler = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-disabler.c',
fallback : disabler())
assert(not is_disabler(version_src_disabler), 'version_src_disabler should not yield a disabler')

version_src_custom = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom.c',
command : ['git', 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')

version_src_custom_input_disabler = vcs_tag(input : disabler(),
output : 'vcstag-custom-input-disabler.c',
command : ['git', 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')
assert(is_disabler(version_src_custom_input_disabler), 'version_src_custom_input_disabler should yield a disabler')

version_src_custom_output_disabler = vcs_tag(input : 'vcstag.c.in',
output : disabler(),
command : ['git', 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')
assert(is_disabler(version_src_custom_output_disabler), 'version_src_custom_output_disabler should yield a disabler')

version_src_custom_command_fallback_disabler = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom-fallback-disabler.c',
command : disabler(),
fallback : disabler())
assert(is_disabler(version_src_custom_command_fallback_disabler), 'version_src_custom_command_fallback_disabler should yield a disabler')

version_src_custom_disabler = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom-disabler.c',
command : [disabler(), 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')
assert(not is_disabler(version_src_custom_disabler), 'version_src_custom_disabler should not yield a disabler')

version_src_custom_disabler_fallback_true = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom-disabler-fallback-true.c',
command : [disabler(), 'show-ref', '-s', 'refs/heads/master'],
fallback : true)
assert(not is_disabler(version_src_custom_disabler_fallback_true), 'version_src_custom_disabler_fallback_true should not yield a disabler')

version_src_custom_disabler_no_fallback = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom-disabler-no-fallback.c',
command : ['git', 'show-ref', '-s', disabler()])
assert(is_disabler(version_src_custom_disabler_no_fallback), 'version_src_custom_disabler_no_fallback should yield a disabler')

version_src_notfound_fallback = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-notfound-fallback.c',
command : ['git-but-not-found-sorry', 'show-ref', '-s', 'refs/heads/master'],
fallback : '1.0.0')

version_src_fallback = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-fallback.c')

git = find_program('git')

version_src_git_program = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-git-program.c',
command : [git, 'rev-parse', 'HEAD'],
fallback : '1.0.0')

version_src_file = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-file.c',
command : files('version.py'))

tagprog = executable('tagprog', 'tagprog.c', version_src)
executable('tagprog-disabler', 'tagprog.c', version_src_disabler)

version_src_executable = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-executable.c',
command : [tagprog],
install: true,
install_dir: get_option('includedir'))

executable('tagprog-custom', 'tagprog.c', version_src_custom)
executable('tagprog-custom-disabler', 'tagprog.c', version_src_custom_disabler)
executable('tagprog-custom-disabler-fallback-true', 'tagprog.c', version_src_custom_disabler_fallback_true)
executable('tagprog-fallback', 'tagprog.c', version_src_fallback)
executable('tagprog-notfound-fallback', 'tagprog.c', version_src_notfound_fallback)
executable('tagprog-git-program', 'tagprog.c', version_src_git_program)
executable('tagprog-executable', 'tagprog.c', version_src_executable)
executable('tagprog-file', 'tagprog.c', version_src_file)
