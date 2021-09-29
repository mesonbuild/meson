# Copyright 2019 Red Hat, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

def parse(lines):
    rules = []
    targets = []
    deps = []
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
            if c == '\\' or c == '$':
                escape = c
                continue
            elif c in (' ', '\n'):
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

Target = collections.namedtuple('Target', ['deps'])

class DepFile:
    def __init__(self, lines):
        rules = parse(lines)
        depfile = {}
        for (targets, deps) in rules:
            for target in targets:
                t = depfile.setdefault(target, Target(deps=set()))
                for dep in deps:
                    t.deps.add(dep)
        self.depfile = depfile

    def get_all_dependencies(self, target, visited=None):
        deps = set()
        if not visited:
            visited = set()
        if target in visited:
            return set()
        visited.add(target)
        target = self.depfile.get(target)
        if not target:
            return set()
        deps.update(target.deps)
        for dep in target.deps:
            deps.update(self.get_all_dependencies(dep, visited))
        return sorted(deps)
