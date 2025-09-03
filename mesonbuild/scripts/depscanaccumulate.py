#!/usr/bin/env python3
from collections import defaultdict
from dataclasses import dataclass
import json
import os
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

class DynDepRule:
    def __init__(self, out: str, imp_outs: T.Optional[T.List[str]], imp_ins: T.List[str]):
        self.output = [f'build {out}']
        if imp_outs:
            imp_out_str = " ".join(imp_outs)
            self.output.append(f" | {imp_out_str}")
        self.output.append(": dyndep")
        if imp_ins:
            imp_ins_str = " ".join(imp_ins)
            self.output.append(" | " + imp_ins_str)
        self.output_str = "".join(self.output) + "\n"

    def __str__(self):
        return self.output_str


class ClangDependencyScanner(CppDependenciesScanner):
    def __init__(self, compilation_db_file, json_output_file, dd_output_file=None):
        self.compilation_db_file = compilation_db_file
        self.json_output_file = json_output_file
        self.dd_output_file = dd_output_file

    def scan(self) -> T.Tuple[T.Mapping[ObjectFile, ModuleName],
                              T.Mapping[ObjectFile, ModuleProviderInfo]]:
        try:
            r = sp.run(["/usr/local/Cellar/llvm/20.1.1/bin/clang-scan-deps",
                        "-format=p1689",
                        "-compilation-database", self.compilation_db_file],
                       capture_output=True)
            if r.returncode != 0:
                print(r.stderr)
                raise sp.SubprocessError("Failed to run command")
            process_output = r.stdout
            with open(self.json_output_file, 'wb') as f:
                f.write(process_output)
            dependencies_info = json.loads(r.stdout)
            all_deps_per_objfile = self.generate_dependencies(dependencies_info["rules"])
            self.generate_dd_file(all_deps_per_objfile)
        except sp.SubprocessError:
            return 1
        except sp.TimeoutExpired:
            return 2

    def generate_dd_file(self, deps_per_object_file):
        with open('deps.dd', "w") as f:
            f.write('ninja_dyndep_version = 1\n')
            for obj, reqprov in deps_per_object_file.items():
                requires, provides = reqprov
                dd = DynDepRule(obj, [p.logical_name + ".pcm" for p in provides],
                                [r + '.pcm' for r in requires])
                f.write(str(dd))

    def generate_dependencies(self, rules: T.List):
        all_entries: T.Mapping[ObjectFile, T.Tuple[T.Set(ModuleName), T.Set(ModuleProviderInfo)]] = defaultdict(lambda: (set(), set()))
        for r in rules:
            obj_processed = r["primary-output"]
            # Add empty entries so that dyndep rule is generated for every file with a potential dyndep rule
            # or ninja will complain
            all_entries[obj_processed] = (set(), set())
            for req in r.get("requires", []):
                all_entries[obj_processed][0].add(req["logical-name"])
            for prov in r.get("provides", []):
                all_entries[obj_processed][1].add(ModuleProviderInfo(
                    logical_name=prov["logical-name"],
                    source_path=prov["source-path"],
                    is_interface=prov.get('is-interface', False)))
        return all_entries

def run(args: T.List[str]) -> int:
    assert len(args) >= 2, 'At least <compilation_db> and <json_output-file> arguments'
    comp_db_path, json_output_path, dd_output = args
    scanner = ClangDependencyScanner(comp_db_path, json_output_path)
    return scanner.scan()

if __name__ == '__main__':
    run(sys.argv[1:])
