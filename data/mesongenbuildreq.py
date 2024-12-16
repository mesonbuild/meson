import subprocess
import json
import sys
deps_json = json.loads(subprocess.run([sys.argv[1], "introspect", "--dependencies", "meson.build"], capture_output=True).stdout)
deps_json = filter(lambda a: a['required'] == True, deps_json)
unsorted_deps = dict(zip([x['name'] for x in deps_json], [x['version'] for x in deps_json]))
unsorted_deps.pop('', None)
deps = {}
deps = dict(sorted(unsorted_deps.items(), key=lambda x: x[0])))

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
