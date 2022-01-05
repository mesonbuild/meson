project('Meson documentation', version: '1.0')

cur_bdir = meson.current_build_dir()

# Only the script knows which files are being generated
docs_gen = custom_target(
    'gen_docs',
    input: files('markdown/index.md'),
    output: 'gen_docs.stamp',
    command: [
        files('../tools/regenerate_docs.py'),
        '--output-dir', cur_bdir,
        '--dummy-output-file', '@OUTPUT@',
    ],
    build_by_default: true,
    install: false)

genrefman = find_program('./genrefman.py')
refman_binary = custom_target(
    'gen_refman_bin',
    input: files('sitemap.txt'),
    output: 'reference_manual.bin',
    depfile: 'reman_dep.d',
    command: [
        genrefman,
        '-l', 'yaml',
        '-g', 'pickle',
        '-o', '@OUTPUT@',
        '--depfile', '@DEPFILE@',
        '--force-color',
    ]
)

refman_md = custom_target(
    'gen_refman_md',
    input: refman_binary,
    output: ['configured_sitemap.txt', 'refman_links.json'],
    command: [
        genrefman,
        '-l', 'pickle',
        '-g', 'md',
        '-s', files('sitemap.txt'),
        '-i', '@INPUT@',
        '-o', '@OUTPUT0@',
        '--link-defs', '@OUTPUT1@',
        '--force-color',
        '--no-modules',
    ],
)

refman_json = custom_target(
    'gen_refman_json',
    build_by_default: true,
    input: refman_binary,
    output: 'reference_manual.json',
    command: [
        genrefman,
        '-l', 'pickle',
        '-g', 'json',
        '-i', '@INPUT@',
        '-o', '@OUTPUT@',
        '--force-color',
    ],
)

refman_man = custom_target(
    'gen_refman_man',
    build_by_default: true,
    input: refman_binary,
    output: 'meson-reference.3',
    command: [
        genrefman,
        '-l', 'pickle',
        '-g', 'man',
        '-i', '@INPUT@',
        '-o', '@OUTPUT@',
        '--force-color',
        '--no-modules',
    ],
)

test('validate_docs', find_program('./jsonvalidator.py'), args: [refman_json])

hotdoc_prog = find_program('hotdoc', version: '>=0.13.7')

hotdoc = import('hotdoc')
documentation = hotdoc.generate_doc(meson.project_name(),
    project_version: meson.project_version(),
    sitemap: refman_md[0],
    build_by_default: true,
    depends: docs_gen,
    index: 'markdown/index.md',
    install: false,
    extra_assets: ['images/'],
    include_paths: ['markdown', cur_bdir],
    default_license: 'CC-BY-SAv4.0',
    html_extra_theme: join_paths('theme', 'extra'),
    git_upload_repository: 'git@github.com:mesonbuild/mesonbuild.github.io.git',
    edit_on_github_repository: 'https://github.com/mesonbuild/meson',
    syntax_highlighting_activate: true,
    keep_markup_in_code_blocks: true,
    extra_extension: meson.current_source_dir() / 'extensions' / 'refman_links.py',
    refman_data_file: refman_md[1],
)

run_target('upload',
    command: [hotdoc_prog, 'run',
      '--conf-file', documentation.config_path(),
      '--git-upload',
      '-vv',
    ],
)
