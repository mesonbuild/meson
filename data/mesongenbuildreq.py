import subprocess
import json
import sys
import os

# Configuration from ENV
ignore_deps = set(os.environ.get("BUILDREQ_IGNORE_DEP", "").split())
only_required = os.environ.get("BUILDREQ_ONLY_REQUIRED", "false").lower() == "true"

# Run introspection
try:
    result = subprocess.run([sys.argv[1], "introspect", "--dependencies", "meson.build"],
                            capture_output=True, text=True, check=True)
    deps_json = json.loads(result.stdout)
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)

deps = {}
for entry in deps_json:
    name = entry['name']
    if name in ignore_deps:
        continue
    if only_required and not entry.get('required', True):
        continue
    deps[name] = entry['version']

for lib, versions in deps.items():
    formatted_versions = []
    for v in versions:
        # Step 1: Remove all spaces to get a "clean" string like ">=2.72.0"
        v = v.replace(" ", "")

        # Step 2: Separate the operator from the version
        # We find where the first digit or letter starts
        pivot = 0
        for i, char in enumerate(v):
            if char.isalnum():
                pivot = i
                break

        # Step 3: Reconstruct with exactly one space: ">= 2.72.0"
        if pivot > 0:
            v = f"{v[:pivot]} {v[pivot:]}"
        formatted_versions.append(v)

    # Step 4: Ensure a space exists before the version block starts
    # This ensures "pkgconfig(lib) >= 1.0" instead of "pkgconfig(lib)>= 1.0"
    version_str = f" {' '.join(formatted_versions)}" if formatted_versions else ""

    line = []
    for prefix in ["cmake", "pkgconfig", "qmake"]:
        buildreq = f"{prefix}({lib}){version_str}"

        # Cleanup: remove trailing operators if version was empty
        if buildreq.endswith(('=', '<', '>')):
            buildreq = buildreq.rstrip('=<>')

        line.append(buildreq)

    print(f"({' or '.join(line)})")
