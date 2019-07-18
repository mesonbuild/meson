project('perlxs', 'c',
  default_options : ['warning_level=2'])

perl = find_program('perl')
perl_dep = dependency('perl')
# XXX: Todo
perlmoddir = get_option('prefix') / 'perl-mod'

if perl_dep.found()
  subdir('storer-lib')

  xsubpp_file_c = run_command(perl, '-MExtUtils::ParseXS', '-Eprint $INC{"ExtUtils/ParseXS.pm"} =~ s{ParseXS\\.pm$}{xsubpp}r').stdout()
  xsubpp_file = files(xsubpp_file_c)
  xsubpp = generator(perl,
    output : '@BASENAME@.c',
    capture : true,
    arguments : [ xsubpp_file_c, '@EXTRA_ARGS@', '@INPUT@' ],
  )

  storer_mod = shared_module('Storer',
    [ xsubpp.process(
        files('Storer.xs'),
        # XXX: regenerate dependency on typemap(s) not recorded
        extra_args : [ '-typemap', './typemap' ],) ],
    implicit_include_directories : true,
    # XXX: should be implicit. only ccopts are needed here
    dependencies : perl_dep,
    link_with : [ slib ],
    # XXX: should be fixed
    name_prefix : '',
    install : true,
    # XXX: should be fixed
    install_dir : perlmoddir / 'auto' / 'Meson' / 'Storer',
  )

  pm_files = files('lib/Meson/Storer.pm')
  install_headers(pm_files,
    # XXX: should be fixed
    install_dir : perlmoddir / 'Meson')

  # XXX: should not require this external helper
  blib_helper_file = files('meson-blib-helper.pl')
  blib_t = [
    custom_target('blib-lib',
        command : [ perl, blib_helper_file, '-pm',
          # XXX: target directory should be automatic
          'Meson', '@INPUT@' ],
        input : [ pm_files, ],
        output: 'blib-lib',),
    custom_target('blib-arch',
        command : [ perl, blib_helper_file, '-so',
          # XXX: target directory should be automatic
          'Meson', '@INPUT@' ],
        input : [ storer_mod, ],
        output: 'blib-arch',),
  ]
  alias_target('blib', blib_t)

  subdir('t')
else
  error('MESON_SKIP_TEST: Perl not found, skipping test.')
endif
