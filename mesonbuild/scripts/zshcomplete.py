#!/usr/bin/python3

'''This file generates completion function definitions for Zsh.'''
# NB: the function definitions are directly passed to the `eval` builtin.
# We must take care not to trust meson introspect's output
# and prevent e. g. code injection.

import argparse
import json
import os
import sys
import typing as T
from shlex import quote


def fsemic(s: str) -> str:
    return s.replace(':', r'\:').replace(r'\\:', r'\:')


def c_style_octal(i: int) -> str:
    return '0{:03}'.format(int(oct(i)[2:]))


def generate_choices(optentry: T.Dict) -> T.Union[T.Iterable, None]:
    '''If a build option can be set to a limited number of values,
       return an iterable of possible values. Otherwise, return None.
    '''
    if optentry['type'] == 'combo':
        return optentry.get('choices', [])
    if optentry['type'] == 'boolean':
        return ('false', 'true')
    return None


def simple_hint(i: T.Any) -> str:
    return '<{}>'.format(i)


def generate_hint(optentry: T.Dict) -> str:
    '''Produce a string representation of a build option's current value.
    '''
    v = optentry['value']

    if optentry['type'] == 'boolean':
        return simple_hint('true' if v else 'false')
    if optentry['name'] == 'install_umask':
        return simple_hint(c_style_octal(v))
    if optentry['type'] == 'integer':
        return simple_hint(int(v))

    return simple_hint(repr(v))


def zsh_tag(k: str) -> str:
    return ''.join(c if ord(c) < 0x80 and c.isalnum() else '-' for c in k)


def generate_compadd_choices(o: T.Dict) -> str:
    '''Generate a compadd invocation with value choices.'''
    # We want to display a readably quoted description string which does
    # not garble single quotes inside the string. shlex.quote() works fine,
    # but uses single quotes on the outside and escapes single quotes as
    # '"'"', which is suboptimal to be read by humans. So we use zsh's
    # builtin (qqq) expansion modifier and not shlex.quote().
    decl = 'descr=' + quote(o['description'])
    value_descr = r'${(qqq)descr//\%/%%}' + quote(' ({})'.format(o['type']))
    choices = generate_choices(o)
    if choices is not None:
        compadd = (
            '_wanted',
            '-V',
            'build-option-values',
            'expl',
            value_descr,
            'compadd -',
            *(quote(i) for i in choices),
        )
    else:
        compadd = (
            '_message',
            '-e',
            'build-option-values',
            value_descr,
        )
    return '\n'.join((
        '    ' + decl,
        '    ' + ' '.join(compadd),
    ))


def complete_buildoptions(i_data: T.Dict) -> str:
    by_section: T.Dict[str, T.List[str]] = {}
    switch_entries = {}
    for opt in i_data:
        # Generate a _describe item spec.
        gr = opt['section']
        name = opt['name']
        descr = '{} {}'.format(opt['description'], generate_hint(opt))
        describe_spec = '{}:{}'.format(fsemic(name), fsemic(descr))
        by_section.setdefault(gr, [])
        by_section[gr].append(quote(describe_spec))

        switch_entries[name] = '\n'.join((
            '  ("{}")'.format(name),
            generate_compadd_choices(opt),
            '  ;;',
        ))

    def user_first(d: T.Dict) -> T.Iterable:
        dd = d.copy()
        try:
            u = dd.pop('user')
            yield ('user', u)
        except KeyError:
            pass
        yield from dd.items()

    alt_decls = []
    alt_words = []
    for k, v in user_first(by_section):
        tag_prefix = zsh_tag(k)
        specs_arr = 'ngroup_{}'.format(tag_prefix)
        # No need to quote; `v` already consists of quoted _describe specs.
        sv = '  local -a {}=(\n    {}\n  )'.format(specs_arr, '\n    '.join(v))
        alt_decls.append(sv)
        word = '{}-options:{} option:(( "${{(@){}}}" ))'.format(
            tag_prefix, k, specs_arr)
        alt_words.append(quote(word))
    body = '\n'.join((
         'if ! compset -P 1 {}; then'.format(r'\*\='),
         '\n'.join(alt_decls),
         '  local -a alternative_argv=( -qS= )',
         '  _alternative -O alternative_argv {}'.format(' '.join(alt_words)),
         '  return',
         'fi\n',
         'local m_optname="{}"'.format(r'${${IPREFIX#-D}%\=}'),
         'local descr',
         'case "$m_optname" in',
         '\n'.join(switch_entries.values()),
         '  *)',
         '    _message "unknown option; cannot offer choices"',
         '  ;;',
         'esac',
    ))
    return body


def compmsg_from_exception(exc: Exception) -> str:
    from traceback import format_exception_only
    lines = format_exception_only(type(exc), exc)
    mfmt = 'cannot complete: {}'
    msgs = [quote(mfmt.format(line.rstrip())) for line in lines]
    return '\n'.join('  ' + '_message ' + msg for msg in msgs)


def path_from_builddir(builddir: str, mode: str) -> str:
    return os.path.join(builddir, 'meson-info', f'intro-{mode}.json')


def run(argv: T.List[str]) -> int:
    try:
        ap = argparse.ArgumentParser(
                exit_on_error=False,
                allow_abbrev=False,
                description=""
                "Generate zsh tab-completion code for the introspection data "
                "of a build directory, or a project."
                )
        modes = ('buildoptions',)
        # If more modes will be supported later, the parser will require
        # at least one of them.
        for i in modes:
            ap.add_argument('--' + i,
                            action='store_const', dest='mode', const=i, required=True)
        ap.add_argument('builddir', action='store')
        a = ap.parse_args(argv)
        if a.builddir == '-':
            istream = sys.stdin
        else:
            istream = open(path_from_builddir(a.builddir, a.mode),
                           encoding='utf-8')
        with istream:
            jd = json.load(istream)
        print(complete_buildoptions(jd))
        return 0
    except Exception as e:
        print(compmsg_from_exception(e))
        return 1
