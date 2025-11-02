#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass
import json
import subprocess as sp
import sys
import typing as T

ModuleName: T.TypeAlias = str
ObjectFile: T.TypeAlias = str


@dataclass(frozen=True)
class ModuleProviderInfo:
    logical_name: ModuleName
    source_path: str
    is_interface: bool = False


class CppDependenciesScanner:
    pass


def normalize_filename(fname):
    return fname.replace(':', '-')


class DynDepRule:
    def __init__(self, out: str, imp_outs: T.Optional[T.List[str]], imp_ins: T.List[str]):
        self.output = [f'build {out}']
        if imp_outs:
            imp_out_str = " ".join([normalize_filename(o) for o in imp_outs])
            self.output.append(f" | {imp_out_str}")
        self.output.append(": dyndep")
        if imp_ins:
            imp_ins_str = " ".join([normalize_filename(inf) for inf in imp_ins])
            self.output.append(" | " + imp_ins_str)
        self.output_str = "".join(self.output) + "\n"

    def __str__(self):
        return self.output_str


class ClangDependencyScanner(CppDependenciesScanner):
    def __init__(self, compilation_db_file, json_output_file, dd_output_file=None):
        self.compilation_db_file = compilation_db_file
        self.json_output_file = json_output_file
        self.dd_output_file = dd_output_file

    def scan(self) -> T.Tuple[T.Mapping[ObjectFile, ModuleName], T.Mapping[ObjectFile, ModuleProviderInfo]]:
        try:
            result = sp.run(
                ["clang-scan-deps",
                 "-format=p1689",
                 "-compilation-database", self.compilation_db_file],
                capture_output=True,
                check=False
            )

            if result.returncode != 0:
                print(result.stderr.decode())
                raise sp.SubprocessError("Failed to run clang-scan-deps")

            with open(self.json_output_file, 'wb') as f:
                f.write(result.stdout)

            dependencies_info = json.loads(result.stdout)
            all_deps_per_objfile = self.generate_dependencies(dependencies_info["rules"])
            self.generate_dd_file(all_deps_per_objfile)
            return 0

        except sp.SubprocessError:
            return 1
        except sp.TimeoutExpired:
            return 2

    def generate_dd_file(self, deps_per_object_file):
        with open('deps.dd', "w") as f:
            f.write('ninja_dyndep_version = 1\n')
            for obj, reqprov in deps_per_object_file.items():
                requires, provides = reqprov
                dd = DynDepRule(
                    obj,
                    [p.logical_name + ".pcm" for p in provides],
                    [r + '.pcm' for r in requires]
                )
                f.write(str(dd))

    def generate_dependencies(self, rules: T.List):
        all_entries: T.Mapping[ObjectFile, T.Tuple[T.Set[ModuleName], T.Set[ModuleProviderInfo]]] = \
            defaultdict(lambda: (set(), set()))

        for r in rules:
            obj_processed = r["primary-output"]
            all_entries[obj_processed] = (set(), set())

            for req in r.get("requires", []):
                all_entries[obj_processed][0].add(req["logical-name"])

            for prov in r.get("provides", []):
                all_entries[obj_processed][1].add(ModuleProviderInfo(
                    logical_name=prov["logical-name"],
                    source_path=prov["source-path"],
                    is_interface=prov.get('is-interface', False)
                ))

        return all_entries


def run(args: T.List[str]) -> int:
    assert len(args) >= 2, 'At least <compilation_db> and <json_output_file> arguments required'
    comp_db_path, json_output_path, dd_output = args
    scanner = ClangDependencyScanner(comp_db_path, json_output_path)
    return scanner.scan()


if __name__ == '__main__':
    run(sys.argv[1:])
