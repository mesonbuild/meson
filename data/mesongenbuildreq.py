import subprocess
import json
import sys
import os

# Read ignored dependencies from ENV
ignore_deps = set(os.environ.get("BUILDREQ_IGNORE_DEP", "").split())

# Run introspection command
deps_json = json.loads(
    subprocess.run(
        [sys.argv[1], "introspect", "--dependencies", "meson.build"],
        capture_output=True,
        text=True
    ).stdout
)

# Build deps dictionary while skipping ignored libraries
deps = {entry['name']: entry['version'] for entry in deps_json if entry['name'] not in ignore_deps}

# Output formatted build requirements
for lib, versions in deps.items():
    # Join versions if available
    version_str = f" {' '.join(versions)} " if versions else ''
    line = [f"{prefix}({lib}){version_str}" for prefix in ["cmake", "pkgconfig", "qmake"]]
    print(f"({' or '.join(line)})")
