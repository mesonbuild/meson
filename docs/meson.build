project('Meson documentation', version: '1.0')

cur_bdir = meson.current_build_dir()

# Copy all files to build dir, since HotDoc uses relative paths
run_command(
    files('../tools/copy_files.py'),
    '-C', meson.current_source_dir(),
    '--output-dir', cur_bdir,
    'markdown', 'theme', 'sitemap.txt', 
    check: true)

# Only the script knows which files are being generated
docs_gen = custom_target(
    'gen_docs',
    input: files('markdown/index.md'),
    output: 'gen_docs.dummy',
    command: [
        files('../tools/regenerate_docs.py'),
        '--output-dir', join_paths(cur_bdir, 'markdown'),
        '--dummy-output-file', '@OUTPUT@',
    ],
    build_by_default: true,
    install: false)

hotdoc = import('hotdoc')
documentation = hotdoc.generate_doc(meson.project_name(),
    project_version: meson.project_version(),
    sitemap: join_paths(cur_bdir, 'sitemap.txt'),
    build_by_default: true,
    depends: docs_gen,
    index: join_paths(cur_bdir, 'markdown/index.md'),
    install: false,
    extra_assets: ['images/'],
    include_paths: [join_paths(cur_bdir, 'markdown')],
    default_license: 'CC-BY-SAv4.0',
    html_extra_theme: join_paths(cur_bdir, 'theme', 'extra'),
    git_upload_repository: 'git@github.com:jpakkane/jpakkane.github.io.git',
    edit_on_github_repository: 'https://github.com/mesonbuild/meson/',
    syntax_highlighting_activate: true,
)

run_target('upload',
    command: [find_program('hotdoc'), 'run', '--conf-file', documentation.config_path()]
)
