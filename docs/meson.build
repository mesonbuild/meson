project('Meson documentation', version: '1.0')

hotdoc = import('hotdoc')
documentation = hotdoc.generate_doc(meson.project_name(),
    project_version: meson.project_version(),
    sitemap: 'sitemap.txt',
    build_by_default: true,
    index: 'markdown/index.md',
    install: false,
    extra_assets: ['images/'],
    include_paths: ['markdown'],
    default_license: 'CC-BY-SAv4.0',
    html_extra_theme: join_paths('theme', 'extra'),
    git_upload_repository: 'git@github.com:jpakkane/jpakkane.github.io.git',
    edit_on_github_repository: 'https://github.com/mesonbuild/meson/',
    syntax_highlighting_activate: true,
)

run_target('upload',
    command: [find_program('hotdoc'), 'run', '--conf-file', documentation.config_path()]
)
