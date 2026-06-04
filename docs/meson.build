project('Meson documentation', version: '1.0')

yaml_modname = get_option('unsafe_yaml') ? 'yaml' : 'strictyaml'
py = import('python').find_installation('python3', modules: [yaml_modname], required: false)
if not py.found()
    error(f'Cannot build documentation without yaml support')
endif

cur_bdir = meson.current_build_dir()

sitemap = files('sitemap.txt')

yaml_loader = get_option('unsafe_yaml') ? 'fastyaml' : 'yaml'
genrefman = find_program('./genrefman.py')
refman_binary = custom_target(
    'gen_refman_bin',
    input: sitemap,
    output: 'reference_manual.bin',
    depfile: 'reman_dep.d',
    command: [
        genrefman,
        '-l', yaml_loader,
        '-g', 'pickle',
        '-o', '@OUTPUT@',
        '--depfile', '@DEPFILE@',
        '--force-color',
    ]
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
test('validate_docs', find_program('./jsonvalidator.py'), args: [refman_json])

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
    install: true,
    install_dir: get_option('mandir') / 'man3',
)

# Everything past here is HTML resources.
if not get_option('html')
    subdir_done()
endif

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
    install: false,
)

refman_md = custom_target(
    'gen_refman_md',
    input: refman_binary,
    output: ['configured_sitemap.txt', 'refman_links.json'],
    command: [
        genrefman,
        '-l', 'pickle',
        '-g', 'md',
        '-s', sitemap,
        '-i', '@INPUT@',
        '-o', '@OUTPUT0@',
        '--link-defs', '@OUTPUT1@',
        '--force-color',
        '--no-modules',
    ],
)

sphinx_build = find_program('sphinx-build', required: true)

sphinx_conf = configure_file(
    input: 'sphinx/conf.py.in',
    output: 'conf.py',
    configuration: {
        'PROJECT_NAME': meson.project_name(),
        'PROJECT_VERSION': meson.project_version(),
        'SPHINX_EXTENSION_DIR': meson.current_source_dir() / 'sphinx',
        'SPHINX_SITEMAP_FILE': refman_md[0].full_path(),
        'REFMAN_DATA_FILE': refman_md[1].full_path(),
        'MESON_LOGO': meson.current_source_dir() / 'theme' / 'extra' / 'images' / 'meson_logo.png',
        'MESON_FAVICON': meson.current_source_dir() / 'theme' / 'extra' / 'images' / 'favicon.png',
    }
)

custom_target(
    'sphinx_docs',
    input: sphinx_conf,
    output: 'sphinx_docs.stamp',
    command: [
        py,
        files('sphinx/run_sphinx.py'),
        sphinx_build,
        meson.current_build_dir(),
        meson.current_source_dir() / 'markdown',
        meson.current_build_dir(),
        meson.current_build_dir() / (meson.project_name() + '-doc') / 'html',
        '@OUTPUT@',
    ],
    depends: [refman_md, docs_gen],
    build_by_default: true,
)

test('validate_links', find_program('./validatelinks.py'), args: meson.current_source_dir() / 'markdown' / 'Users.md', timeout: 65)
