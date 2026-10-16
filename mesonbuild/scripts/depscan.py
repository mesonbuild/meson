# SPDX-License-Identifier: Apache-2.0
# Copyright 2020 The Meson development team
# Copyright © 2023-2024 Intel Corporation

from __future__ import annotations

import collections
import json
import os
import pathlib
import pickle
import re
import typing as T

if T.TYPE_CHECKING:
    from typing_extensions import Literal, TypedDict, NotRequired
    from ..backend.ninjabackend import TargetDependencyScannerInfo

    Require = TypedDict(
        'Require',
        {
            'logical-name': str,
            'compiled-module-path': NotRequired[str],
            'source-path': NotRequired[str],
            'unique-on-source-path': NotRequired[bool],
            'lookup-method': NotRequired[Literal['by-name', 'include-angle', 'include-quote']]
        },
    )

    Provide = TypedDict(
        'Provide',
        {
            'logical-name': str,
            'compiled-module-path': NotRequired[str],
            'source-path': NotRequired[str],
            'unique-on-source-path': NotRequired[bool],
            'is-interface': NotRequired[bool],
        },
    )

    Rule = TypedDict(
        'Rule',
        {
            'primary-output': NotRequired[str],
            'outputs': NotRequired[T.List[str]],
            'provides': NotRequired[T.List[Provide]],
            'requires': NotRequired[T.List[Require]],
        }
    )

    class Description(TypedDict):

        version: int
        revision: int
        rules: T.List[Rule]


# Module names are dot separated identifiers, such as `foo` or `foo.bar`.
# Header units (`import <foo>;` and `import "foo.h";`) are not matched.
CPP_MODULE_NAME_PAT = r'\w+(?:\.\w+)*'
CPP_IMPORT_RE = re.compile(rf'\s*(?:export\s+)?import\s+({CPP_MODULE_NAME_PAT})\s*;')
# `import :part;` imports a partition of the module the current unit belongs to.
CPP_PARTITION_IMPORT_RE = re.compile(rf'\s*(?:export\s+)?import\s*:\s*({CPP_MODULE_NAME_PAT})\s*;')
# `[export] module name[:part];`
CPP_MODULE_RE = re.compile(rf'\s*(export\s+)?module\s+({CPP_MODULE_NAME_PAT})\s*(?::\s*({CPP_MODULE_NAME_PAT})\s*)?;')

# Comments and literals, which may contain text looking like module
# declarations. Raw strings are matched before plain strings, and the
# lookbehind on character literals skips digit separators (`1'000`).
CPP_COMMENT_OR_LITERAL_RE = re.compile(
    r'//[^\n]*'
    r'|/\*.*?\*/'
    r'|(?<!\w)(?:u8|u|U|L)?R"([^()\\\s]{0,16})\(.*?\)\1"'
    r'|"(?:\\.|[^"\\\n])*"'
    r"|(?<!\w)'(?:\\.|[^'\\\n])*'",
    re.DOTALL)
CPP_IF_ZERO_RE = re.compile(r'\s*#\s*if\s+0\s*$')
CPP_IF_RE = re.compile(r'\s*#\s*if(?:n?def)?\b')
CPP_ELSE_RE = re.compile(r'\s*#\s*(?:else|elif(?:n?def)?)\b')
CPP_ENDIF_RE = re.compile(r'\s*#\s*endif\b')


def _remove_cpp_inactive_text(text: str) -> T.List[str]:
    """Remove comments, literals and `#if 0` blocks from C++ source.

    Other preprocessor conditionals are not evaluated.

    :param text: The contents of the source file
    :return: The remaining lines of the file
    """
    # Keep the newlines of what is removed so lines stay where they are.
    text = CPP_COMMENT_OR_LITERAL_RE.sub(lambda m: ' ' + '\n' * m.group(0).count('\n'), text)
    lines: T.List[str] = []
    # Nesting level inside the `#if 0` block being skipped, 0 when not skipping.
    depth = 0
    for line in text.split('\n'):
        if depth == 0:
            if CPP_IF_ZERO_RE.match(line):
                depth = 1
            else:
                lines.append(line)
        elif CPP_IF_RE.match(line):
            depth += 1
        elif CPP_ENDIF_RE.match(line):
            depth -= 1
        elif depth == 1 and CPP_ELSE_RE.match(line):
            # The `#else` or `#elif` branch of `#if 0` may be active.
            depth = 0
    return lines

FORTRAN_INCLUDE_PAT = r"^\s*include\s*['\"](\w+\.\w+)['\"]"
FORTRAN_MODULE_PAT = r"^\s*\bmodule\b\s+(\w+)\s*(?:!+.*)*$"
FORTRAN_SUBMOD_PAT = r"^\s*\bsubmodule\b\s*\((\w+:?\w+)\)\s*(\w+)"
FORTRAN_USE_PAT = r"^\s*use,?\s*(?:non_intrinsic)?\s*(?:::)?\s*(\w+)"

FORTRAN_MODULE_RE = re.compile(FORTRAN_MODULE_PAT, re.IGNORECASE)
FORTRAN_SUBMOD_RE = re.compile(FORTRAN_SUBMOD_PAT, re.IGNORECASE)
FORTRAN_USE_RE = re.compile(FORTRAN_USE_PAT, re.IGNORECASE)


def parse_cpp_module_declarations(text: str) -> T.Tuple[T.List[str], T.List[str]]:
    exports: T.List[str] = []
    imports: T.List[str] = []
    # The module the current unit belongs to, needed to resolve partition imports.
    module_name: T.Optional[str] = None
    for line in _remove_cpp_inactive_text(text):
        module_match = CPP_MODULE_RE.match(line)
        if module_match:
            exported, module_name, partition = module_match.groups()
            if partition:
                # Both interface (`export module a:b;`) and internal
                # (`module a:b;`) partitions provide `a:b`.
                exports.append(f'{module_name}:{partition}')
            elif exported:
                exports.append(module_name)
            else:
                # An implementation unit (`module a;`) implicitly imports
                # its primary module interface.
                imports.append(module_name)
            continue
        import_match = CPP_IMPORT_RE.match(line)
        if import_match:
            imports.append(import_match.group(1))
            continue
        partition_import_match = CPP_PARTITION_IMPORT_RE.match(line)
        if partition_import_match and module_name:
            imports.append(f'{module_name}:{partition_import_match.group(1)}')
    return exports, imports


class DependencyScanner:
    def __init__(self, pickle_file: str, outfile: str):
        with open(pickle_file, 'rb') as pf:
            self.target_data: TargetDependencyScannerInfo = pickle.load(pf)
        self.outfile = outfile
        self.sources = self.target_data.sources
        self.provided_by: T.Dict[str, str] = {}
        self.exports: T.Dict[str, str] = {}
        self.imports: collections.defaultdict[str, T.List[str]] = collections.defaultdict(list)
        self.sources_with_exports: T.List[str] = []

    def scan_file(self, fname: str, lang: Literal['cpp', 'fortran']) -> None:
        if lang == 'fortran':
            self.scan_fortran_file(fname)
        else:
            self.scan_cpp_file(fname)

    def scan_fortran_file(self, fname: str) -> None:
        fpath = pathlib.Path(fname)
        modules_in_this_file = set()
        for line in fpath.read_text(encoding='utf-8-sig', errors='ignore').split('\n'):
            import_match = FORTRAN_USE_RE.match(line)
            export_match = FORTRAN_MODULE_RE.match(line)
            submodule_export_match = FORTRAN_SUBMOD_RE.match(line)
            if import_match:
                needed = import_match.group(1).lower()
                # In Fortran you have an using declaration also for the module
                # you define in the same file. Prevent circular dependencies.
                if needed not in modules_in_this_file:
                    self.imports[fname].append(needed)
            if export_match:
                exported_module = export_match.group(1).lower()
                assert exported_module not in modules_in_this_file
                modules_in_this_file.add(exported_module)
                if exported_module in self.provided_by:
                    raise RuntimeError(f'Multiple files provide module {exported_module}.')
                self.sources_with_exports.append(fname)
                self.provided_by[exported_module] = fname
                self.exports[fname] = exported_module
            if submodule_export_match:
                # Store submodule "Foo" "Bar" as "foo:bar".
                # A submodule declaration can be both an import and an export declaration:
                #
                # submodule (a1:a2) a3
                #  - requires a1@a2.smod
                #  - produces a1@a3.smod
                parent_module_name_full = submodule_export_match.group(1).lower()
                parent_module_name = parent_module_name_full.split(':')[0]
                submodule_name = submodule_export_match.group(2).lower()
                concat_name = f'{parent_module_name}:{submodule_name}'
                self.sources_with_exports.append(fname)
                self.provided_by[concat_name] = fname
                self.exports[fname] = concat_name
                # Fortran requires that the immediate parent module must be built
                # before the current one. Thus:
                #
                # submodule (parent) parent   <- requires parent.mod (really parent.smod, but they are created at the same time)
                # submodule (a1:a2) a3        <- requires a1@a2.smod
                #
                # a3 does not depend on the a1 parent module directly, only transitively.
                self.imports[fname].append(parent_module_name_full)

    def scan_cpp_file(self, fname: str) -> None:
        fpath = pathlib.Path(fname)
        exports, imports = parse_cpp_module_declarations(fpath.read_text(encoding='utf-8-sig', errors='ignore'))
        if imports:
            self.imports[fname].extend(imports)
        for exported_module in exports:
            if exported_module in self.provided_by:
                raise RuntimeError(f'Multiple files provide module {exported_module}.')
            self.sources_with_exports.append(fname)
            self.provided_by[exported_module] = fname
            self.exports[fname] = exported_module

    def module_name_for(self, src: str, lang: Literal['cpp', 'fortran']) -> str:
        if lang == 'fortran':
            exported = self.exports[src]
            # Module foo:bar goes to a file name foo@bar.smod
            # Module Foo goes to a file name foo.mod
            namebase = exported.replace(':', '@')
            if ':' in exported:
                extension = 'smod'
            else:
                extension = 'mod'
            return os.path.join(self.target_data.private_dir, f'{namebase}.{extension}')
        # Partition a:b goes to a file named a-b
        namebase = self.exports[src].replace(':', '-')
        if self.target_data.cpp_compiler_id == 'gcc':
            # The default module mapper of GCC puts the files in gcm.cache,
            # relative to the working directory of the compiler.
            return os.path.join('gcm.cache', f'{namebase}.gcm')
        return f'{namebase}.ifc'

    def scan(self) -> int:
        for s, lang in self.sources:
            self.scan_file(s, lang)
        description: Description = {
            'version': 1,
            'revision': 0,
            'rules': [],
        }
        for src, lang in self.sources:
            rule: Rule = {
                'primary-output': self.target_data.source2object[src],
                'requires': [],
                'provides': [],
            }
            if src in self.sources_with_exports:
                rule['outputs'] = [self.module_name_for(src, lang)]
            if src in self.imports:
                for modname in self.imports[src]:
                    provider_src = self.provided_by.get(modname)
                    if provider_src == src:
                        continue
                    rule['requires'].append({
                        'logical-name': modname,
                    })
                    if provider_src:
                        rule['requires'][-1].update({
                            'source-path': provider_src,
                            'compiled-module-path': self.module_name_for(provider_src, lang),
                        })
            if src in self.exports:
                modname = self.exports[src]
                rule['provides'].append({
                    'logical-name': modname,
                    'source-path': src,
                    'compiled-module-path': self.module_name_for(src, lang),
                })
            description['rules'].append(rule)

        with open(self.outfile, 'w', encoding='utf-8') as f:
            json.dump(description, f)

        return 0

def run(args: T.List[str]) -> int:
    assert len(args) == 2, 'got wrong number of arguments!'
    outfile, pickle_file = args
    scanner = DependencyScanner(pickle_file, outfile)
    return scanner.scan()
