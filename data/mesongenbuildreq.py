import subprocess
import json
import sys
import os

#buildreq: prefix of build req dep, eg cmake()
# method: discovery method as outlined in the introspect command
def generate (method: list[str], buildreq: list[str], deps_json: dict):
    deps = {entry['name']: entry['version']
            for entry in deps_json
            if (entry['method'] in method)}

    # Output formatted build requirements
    for lib, versions in deps.items():
        # Join versions if available
        version_str = f" {' '.join(versions)} " if versions else ''
        line = [f"{prefix}({lib}){version_str}" for prefix in buildreq]
        print(f"({' or '.join(line)})")

# Read ignored dependencies from ENV
ignore_deps = set(os.environ.get("BUILDREQ_IGNORE_DEP", "").split())
required_only = os.getenv("BUILDREQ_REQUIRED_ONLY") is not None

# Run introspection command
deps_json = json.loads(
    subprocess.run(
        [sys.argv[1], "introspect", "--dependencies", "meson.build"],
        capture_output=True,
        text=True
    ).stdout
)

# pre-run one-time filters

deps_json = {dep for dep in deps_json if (dep['name'] not in ignore_deps)}
if required_only:
    deps_json = {dep for dep in deps_json if dep['required'] == "true"}

#main part
generate(['cmake', 'pkg-config', 'qmake', 'auto'],
         ['cmake', 'pkgconfig', 'qmake'],
         deps_json)
generate(['sysconfig'],
         ['python3dist'],
         deps_json)




