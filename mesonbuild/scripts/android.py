# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026  Florian Leander Singer <sp1rit@disroot.org>

import typing as T
import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

def modinfo_generate(args: T.List[str]) -> int:
    if len(args) != 3:
        print('Usage: modinfo-generate <OUTPUT> <path/to/jar.jar> <module name>')
        return 2

    with ZipFile(args[1]) as system_core_jar:
        pat = re.compile(r"(.*)/[^/]*.class")
        packages = sorted({m.group(1).replace('/', '.') for file in system_core_jar.namelist() if (m := pat.search(file))})

    with open(args[0], 'w', encoding='utf-8') as f:
        f.write(f'module {args[2]} {{')
        for package in packages:
            f.write(f'\texports {package};\n')
        f.write('}')

    return 0

zipmerge_parser = argparse.ArgumentParser()
zipmerge_parser.add_argument('output')
zipmerge_parser.add_argument('input', nargs='*')
# Ignore manifest.mf as it contains unnecessary data causing build cache misses, b/234820480.
zipmerge_parser.add_argument('--ignore-manifest', action='store_true')
def zipmerge(args: T.List[str]) -> int:
    parsed = zipmerge_parser.parse_args(args)
    with ZipFile(parsed.output, mode='w') as outzip:
        for infile in parsed.input:
            try:
                with ZipFile(infile) as inzip:
                    for member in inzip.infolist():
                        if parsed.ignore_manifest and member.filename.casefold() == 'meta-inf/manifest.mf':
                            continue
                        if member.is_dir():
                            outzip.mkdir(member)
                        else:
                            outzip.writestr(member, inzip.read(member.filename))
            except BadZipFile:
                # Assume infile is plain file to be added
                outzip.write(infile, os.path.basename(infile))
    return 0

def jmod(args: T.List[str]) -> int:
    if len(args) < 2:
        print('Usage: jmod <OUTPUT> </path/to/jmod> [ARGS ...]')
        return 2

    try:
        os.remove(args[0])
    except OSError:
        pass

    subprocess.check_call(args[1:] + [args[0]])
    return 0

# jlink is a bit annoying. Not only does it produce a directory (cause
# the JVM system image is a directory)
# To work arround these issues, we generate a "faux" output right next
# to the directory for ninja to work with.
def jlink(args: T.List[str]) -> int:
    if len(args) < 3:
        print('Usage: jlink <OUTPUT> </path/to/jrt-fs.jar> </path/to/jlink> [ARGS ...]')
        return 2

    output = args[0]
    try:
        shutil.rmtree(output)
    except FileNotFoundError:
        pass

    subprocess.check_call(args[2:] + ['--output', output])
    with open(f'{os.path.normpath(output)}.tgt', 'wb'):
        pass

    os.makedirs(os.path.join(output, 'lib'), exist_ok=True)
    return zipmerge([
        os.path.join(output, 'lib', 'jrt-fs.jar'),
        '--ignore-manifest', args[1]
    ])

manifest_rewriter_parser = argparse.ArgumentParser()
manifest_rewriter_parser.add_argument('manifest')
manifest_rewriter_parser.add_argument('--output', action='store', required=True)
manifest_rewriter_parser.add_argument('--appid', action='store')
def manifest_rewriter(args: T.List[str]) -> int:
    parsed = manifest_rewriter_parser.parse_args(args)
    manifest = ET.parse(parsed.manifest)
    mf_root = manifest.getroot()
    if mf_root is None or mf_root.tag != 'manifest':
        print(f'Manifest {parsed.manifest} is not a valid android manifest', file=sys.stderr)
        return 1
    if parsed.appid is not None:
        mf_root.set('package', parsed.appid)
    manifest.write(parsed.output, encoding="utf-8", xml_declaration=True)
    return 0

SUBCOMMANDS: T.Dict[str, T.Callable[[T.List[str]], int]] = {
    'modinfo-generate': modinfo_generate,
    'zipmerge': zipmerge,
    'jmod': jmod,
    'jlink': jlink,

    'manifest-rewriter': manifest_rewriter
}

def run(args: T.List[str]) -> int:
    if not args or args[0] not in SUBCOMMANDS:
        print('Unknown subcommand')
        return 2
    return SUBCOMMANDS[args[0]](args[1:])
