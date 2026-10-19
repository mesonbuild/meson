# SPDX-License-Identifier: Apache-2.0
# Copyright © 2021-2024 Intel Corporation

"""Accumulator for p1689r5 module dependencies.

See: https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2022/p1689r5.html
"""

from __future__ import annotations
import json
import re
import textwrap
import typing as T

if T.TYPE_CHECKING:
    from .depscan import Description, Rule

# The quoting logic has been copied from the ninjabackend to avoid having to
# import half of Meson just to quote outputs, which is a performance problem
_QUOTE_PAT = re.compile(r'[$ :\n]')


def quote(text: str) -> str:
    # Fast path for when no quoting is necessary
    if not _QUOTE_PAT.search(text):
        return text
    if '\n' in text:
        errmsg = textwrap.dedent(f'''\
            Ninja does not support newlines in rules. The content was:

            {text}

            Please report this error with a test case to the Meson bug tracker.''')
        raise RuntimeError(errmsg)
    return _QUOTE_PAT.sub(r'$\g<0>', text)


_PROVIDER_CACHE: T.Dict[str, str] = {}


def get_provider(rules: T.List[Rule], name: str) -> T.Optional[str]:
    """Get the object that a module from another Target provides

    We must rely on the object file here instead of the module itself, because
    the object rule is part of the generated build.ninja, while the module is
    only declared inside a dyndep. This creates for the dyndep generator to
    depend on previous dyndeps as order deps. Since the module
    interface file will be generated when the object is generated we can rely on
    that in proxy and simplify generation.

    :param rules: The list of rules to check
    :param name: The logical-name to look for
    :raises RuntimeError: If no provider can be found
    :return: The object file of the rule providing the module
    """
    # Cache the result for performance reasons
    if name in _PROVIDER_CACHE:
        return _PROVIDER_CACHE[name]

    for r in rules:
        for p in r.get('provides', []):
            if p['logical-name'] == name:
                obj = r['primary-output']
                _PROVIDER_CACHE[name] = obj
                return obj
    return None


def bmi_path(pattern: str, module: str) -> str:
    """The compiled module file for a module, a partition a:b is stored as a-b"""
    return pattern.format(module=module.replace(':', '-'))


def process_rules(rules: T.List[Rule],
                  extra_rules: T.List[Rule],
                  bmi_pattern: T.Optional[str] = None,
                  ) -> T.Iterable[T.Tuple[str, T.Optional[T.List[str]], T.List[str]]]:
    """Process the rules for this Target

    :param rules: the rules for this target
    :param extra_rules: the rules for all of the targets this one links with, to use their provides
    :param bmi_pattern: where compiled modules are written, for the scanners which do not tell
    :yield: A tuple of the output, the exported modules, and the consumed modules
    """
    provided = {p['logical-name'] for rule in rules for p in rule.get('provides', [])}
    for rule in rules:
        prov: T.Optional[T.List[str]] = None
        req: T.List[str] = []
        if 'provides' in rule:
            prov = []
            for p in rule['provides']:
                modfile = p.get('compiled-module-path')
                if modfile is None and bmi_pattern:
                    modfile = bmi_path(bmi_pattern, p['logical-name'])
                if modfile is not None:
                    prov.append(modfile)
        if 'requires' in rule:
            for r in rule['requires']:
                modfile = r.get('compiled-module-path')
                if modfile is None and bmi_pattern and r['logical-name'] in provided:
                    modfile = bmi_path(bmi_pattern, r['logical-name'])
                if modfile is not None:
                    req.append(modfile)
                else:
                    # We can't error if this is not found because of compiler
                    # provided modules
                    found = get_provider(extra_rules, r['logical-name'])
                    if found:
                        req.append(found)
        yield rule['primary-output'], prov, req


def formatter(files: T.Optional[T.List[str]]) -> str:
    if files:
        fmt = ' '.join(quote(f) for f in files)
        return f'| {fmt}'
    return ''


def gen(outfile: str, rules: T.List[Rule], extra_rules: T.List[Rule],
        bmi_pattern: T.Optional[str] = None) -> int:
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write('ninja_dyndep_version = 1\n\n')

        for obj, provides, requires in process_rules(rules, extra_rules, bmi_pattern):
            ins = formatter(requires)
            out = formatter(provides)
            f.write(f'build {quote(obj)} {out}: dyndep {ins}\n\n')

    return 0


def run(args: T.List[str]) -> int:
    """Arguments: [--own N] [--bmi-pattern PATTERN] OUTFILE JSONFILE...

    The first N (default 1) description files are the ones of this target, the
    others are the ones of the targets it links with.
    """
    own = 1
    bmi_pattern: T.Optional[str] = None
    while args and args[0] in {'--own', '--bmi-pattern'}:
        if len(args) < 2:
            raise RuntimeError(f'{args[0]} needs a value')
        if args[0] == '--own':
            own = int(args[1])
        else:
            bmi_pattern = args[1]
        args = args[2:]
    assert len(args) >= 2, 'got wrong number of arguments!'
    outfile, *jsonfiles = args

    # All rules, necessary for fulfilling across TU and target boundaries
    rules: T.List[Rule] = []
    own_rules: T.List[Rule] = []
    for i, jsonfile in enumerate(jsonfiles):
        with open(jsonfile, 'r', encoding='utf-8') as f:
            desc: Description = json.load(f)
        rules.extend(desc['rules'])
        if i < own:
            own_rules.extend(desc['rules'])

    return gen(outfile, own_rules, rules, bmi_pattern)
