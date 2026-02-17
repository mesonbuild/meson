from collections import defaultdict
from dataclasses import dataclass
import json
import os
import subprocess as sp
import sys
import typing as T
import shutil

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
    def __init__(self, compilation_db_file: str, json_output_file: str, dd_output_file: str = 'deps.dd', cpp_compiler: str = 'clang++'):
        self.compilation_db_file = compilation_db_file
        self.json_output_file = json_output_file
        self.dd_output_file = dd_output_file
        self.clang_scan_deps = os.path.join(os.path.dirname(shutil.which(cpp_compiler)), 'clang-scan-deps')

    def scan(self) -> int:
        try:
            with open(self.compilation_db_file, 'r') as f:
                compile_commands = json.load(f)

            cpp_extensions = {'.cpp', '.cc', '.cxx', '.c++', '.cppm'}
            cpp_commands = [cmd for cmd in compile_commands
                            if os.path.splitext(cmd['file'])[1] in cpp_extensions]

            filtered_db = self.compilation_db_file + '.filtered.json'
            with open(filtered_db, 'w') as f:
                json.dump(cpp_commands, f)

            r = sp.run([self.clang_scan_deps,
                        "-format=p1689",
                        "-compilation-database", filtered_db],
                    capture_output=True)
            if r.returncode != 0:
                print(r.stderr)
                raise sp.SubprocessError("Failed to run command")
            with open(self.json_output_file, 'wb') as f:
                f.write(r.stdout)
            dependencies_info = json.loads(r.stdout)
            all_deps_per_objfile = self.generate_dependencies(dependencies_info["rules"])
            self.generate_dd_file(all_deps_per_objfile)
            return 0
        except sp.SubprocessError:
            return 1

    def generate_dd_file(self, deps_per_object_file):
        with open(self.dd_output_file, "w") as f:
            f.write('ninja_dyndep_version = 1\n')
            for obj, reqprov in deps_per_object_file.items():
                requires, provides = reqprov
                dd = DynDepRule(obj, None,
                                [r + '.pcm' for r in requires])
                f.write(str(dd))

    def generate_dependencies(self, rules: T.List):
        all_entries: T.Mapping[ObjectFile, T.Tuple[T.Set[ModuleName], T.Set[ModuleProviderInfo]]] = defaultdict(lambda: (set(), set()))
        for r in rules:
            obj_processed = r["primary-output"]
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
    assert len(args) >= 3, 'Expected <compilation_db> <json_output> <dd_output> [cpp_compiler] arguments'
    comp_db_path, json_output_path, dd_output = args[:3]
    cpp = args[3] if len(args) > 3 else 'clang++'
    scanner = ClangDependencyScanner(comp_db_path, json_output_path, dd_output, cpp)
    return scanner.scan()

if __name__ == '__main__':
    run(sys.argv[1:])
