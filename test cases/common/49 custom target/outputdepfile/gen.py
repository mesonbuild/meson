#!/usr/bin/env python3

import sys

_, depfile, output = sys.argv

# Record the path Meson passed as @DEPFILE@ so tests can check it even
# after ninja has ingested (and discarded) the gcc-style depfile.
with open(output + '.path', 'w', encoding='utf-8') as f:
    f.write(depfile.replace('\\', '/'))

with open(output, 'w', encoding='utf-8') as f:
    f.write('generated\n')

quoted_dep = sys.argv[0].replace('\\', '/').replace(' ', r'\ ')
with open(depfile, 'w', encoding='utf-8') as f:
    f.write('{}: {}\n'.format(output.replace('\\', '/'), quoted_dep))
