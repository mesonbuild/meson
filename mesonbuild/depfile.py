# SPDX-License-Identifier: Apache-2.0
# Copyright 2019 Red Hat, Inc.

from __future__ import annotations

import typing as T


def parse(lines: T.Iterable[str]) -> list[tuple[list[str], list[str]]]:
    rules: list[tuple[list[str], list[str]]] = []
    targets: list[str] = []
    deps: list[str] = []
    in_deps = False
    out = ''
    for line in lines:
        if not line.endswith('\n'):
            line += '\n'
        escape = None
        for c in line:
            if escape:
                if escape == '$' and c != '$':
                    out += '$'
                if escape == '\\' and c == '\n':
                    continue
                out += c
                escape = None
                continue
            if c in {'\\', '$'}:
                escape = c
                continue
            elif c in {' ', '\n'}:
                if out != '':
                    if in_deps:
                        deps.append(out)
                    else:
                        targets.append(out)
                out = ''
                if c == '\n':
                    rules.append((targets, deps))
                    targets = []
                    deps = []
                    in_deps = False
                continue
            elif c == ':':
                targets.append(out)
                out = ''
                in_deps = True
                continue
            out += c
    return rules

class Target(T.NamedTuple):

    deps: set[str]


class DepFile:
    def __init__(self, lines: T.Iterable[str]):
        rules = parse(lines)
        depfile: dict[str, Target] = {}
        for (targets, deps) in rules:
            for target in targets:
                t = depfile.setdefault(target, Target(deps=set()))
                for dep in deps:
                    t.deps.add(dep)
        self.depfile = depfile

    def get_all_dependencies(self, name: str, visited: set[str] | None = None) -> list[str]:
        deps: set[str] = set()
        if not visited:
            visited = set()
        if name in visited:
            return []
        visited.add(name)

        target = self.depfile.get(name)
        if not target:
            return []
        deps.update(target.deps)
        for dep in target.deps:
            deps.update(self.get_all_dependencies(dep, visited))
        return sorted(deps)
