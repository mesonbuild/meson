import subprocess
import json
import sys
deps_json = json.loads(subprocess.run([sys.argv[1], "introspect", "--dependencies", "meson.build"], capture_output=True).stdout)
unsorted_deps = dict(zip([x['name'] for x in deps_json],[x['version'] for x in deps_json]))
unsorted_deps.pop('', None)
deps = {}
for lib in list(unsorted_deps.keys()) :
    deps[lib] = unsorted_deps[lib]
for lib, versions in deps.items() :
     # Prepare version constraint
     version_str = ' ' + ' '.join(versions) if versions else ''
     line = []
     for prefix in ["cmake", "pkgconfig", "qmake"] :
         buildreq = (f"{prefix}({lib}){version_str}")
         if buildreq.split('=')[-1] == '' and '=' in buildreq :
             buildreq = buildreq.split('=')[0]
         line.append(buildreq)
     print(f"({' or '.join(line)})")
