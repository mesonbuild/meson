import subprocess 
import json 
import sys
deps_json = \
    json.loads(subprocess.run([ \
        sys.argv[0], \
        "introspect", \
        "--dependencies", \
        "meson.build"], \
    capture_output=True).stdout) \
deps = dict(zip( \
    [x['name'] for x in deps_json], \
    [x['version'] for x in deps_json])) 
deps.pop('', None) 
for lib, versions in deps.items() : 
     # Mapping for special cases 
    pkg_map = { 
        'qt6': 'qmake',
        'KF6WindowSystem': 'cmake',
        'gtk+-3.0': 'pkgconfig',
        'dbus-1': 'pkgconfig',
        'ncursesw': 'pkgconfig',
        'harfbuzz': 'pkgconfig',
        'fribidi': 'pkgconfig',
        # Add more mappings as needed
    }
        
    # Determine the prefix
    prefix = pkg_map.get(lib, 'pkgconfig')
        
     # Prepare version constraint
    version_str = ' ' + ' '.join(versions) if versions else ''
        
    # Generate BuildRequires line
    print(f"BuildRequires: {prefix}({lib}){version_str}") 
