# This file is for testing meson format with editor config

project('default format')

meson_cmd = find_program('meson')
meson_files = {
	'self': files('meson.build'),
	'comments': files('crazy_comments.meson'),
	'indentation': files('indentation.meson'),
	'subdir editorconfig': files('subdir/sub.meson'),
}

foreach name, f : meson_files
	test(
		name,
		meson_cmd,
		args: ['format', '-e', '--check-only', f],
	)

	# Test that .editorconfig can also be loaded from options file
	test(
		name + '-fromconfig',
		meson_cmd,
		args: [
			'format',
			'-c',
			files('options.ini'),
			'--check-only',
			f,
		],
	)
endforeach
