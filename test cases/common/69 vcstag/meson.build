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
assert(not is_disabler(version_src_custom_disabler), 'version_src_custom_disabler_fallback_true should not yield a disabler')

version_src_custom_disabler_no_fallback = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-custom-disabler-no-fallback.c',
command : ['git', 'show-ref', '-s', disabler()])
assert(is_disabler(version_src_custom_disabler_no_fallback), 'version_src_custom_disabler_no_fallback should yield a disabler')

version_src_fallback = vcs_tag(input : 'vcstag.c.in',
output : 'vcstag-fallback.c')

executable('tagprog', 'tagprog.c', version_src)
executable('tagprog-disabler', 'tagprog.c', version_src_disabler)
executable('tagprog-custom', 'tagprog.c', version_src_custom)
executable('tagprog-custom-disabler', 'tagprog.c', version_src_custom_disabler)
executable('tagprog-custom-disabler-fallback-true', 'tagprog.c', version_src_custom_disabler_fallback_true)
executable('tagprog-fallback', 'tagprog.c', version_src_fallback)

