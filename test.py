from nose.tools import *

from glob import glob
from functools import partial, update_wrapper
import os
import platform
import shutil
import subprocess
import sys

import environment
import mesonlib

print_debug = 'MESON_PRINT_TEST_OUTPUT' in os.environ

test_build_dir = 'work area'
install_dir = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'install dir')
meson_command = './meson.py'

#unity_flags = ['--unity']
unity_flags = []

backend_flags = None
compile_commands = None
test_commands = None
install_commands = None

pbfile = None

@nottest
def setup_commands(backend):
    global backend_flags, compile_commands, test_commands, install_commands
    msbuild_exe = shutil.which('msbuild')
    if backend == 'vs2010' or (backend is None and msbuild_exe is not None):
        backend_flags = ['--backend=vs2010']
        compile_commands = ['msbuild']
        test_commands = ['msbuild', 'RUN_TESTS.vcxproj']
        install_commands = []
    elif backend == 'xcode' or (backend is None and mesonlib.is_osx()):
        backend_flags = ['--backend=xcode']
        compile_commands = ['xcodebuild']
        test_commands = ['xcodebuild', '-target', 'RUN_TESTS']
        install_commands = []
    else:
        backend_flags = []
        ninja_command = environment.detect_ninja()
        if ninja_command is None:
            raise RuntimeError('Could not find Ninja executable.')
        if print_debug:
            compile_commands = [ninja_command, '-v']
        else:
            compile_commands = [ninja_command]
        test_commands = [ninja_command, 'test']
        install_commands = [ninja_command, 'install']

@nottest
def platform_fix_filename(fname):
    if platform.system() == 'Darwin':
        if fname.endswith('.so'):
            return fname[:-2] + 'dylib'
        return fname.replace('.so.', '.dylib.')
    elif platform.system() == 'Windows':
        if fname.endswith('.so'):
            (p, f) = os.path.split(fname)
            f = f[3:-2] + 'dll'
            return os.path.join(p, f)
        if fname.endswith('.a'):
            return fname[:-1] + 'lib'
    return fname

@nottest
def validate_install(srcdir, installdir):
    if platform.system() == 'Windows':
        # Don't really know how Windows installs should work
        # so skip.
        return ''
    info_file = os.path.join(srcdir, 'installed_files.txt')
    expected = {}
    found = {}
    if os.path.exists(info_file):
        with open(info_file) as f:
            for line in f:
                expected[platform_fix_filename(line.strip())] = True
    for root, _, files in os.walk(installdir):
        for fname in files:
            found_name = os.path.join(root, fname)[len(installdir)+1:]
            found[found_name] = True
    expected = set(expected)
    found = set(found)
    missing = expected - found
    for fname in missing:
        return 'Expected file %s missing.' % fname
    extra = found - expected
    for fname in extra:
        return 'Found extra file %s.' % fname
    return ''

@nottest
def run_test(testdir, should_succeed):
    global compile_commands
    shutil.rmtree(test_build_dir)
    shutil.rmtree(install_dir)
    os.mkdir(test_build_dir)
    os.mkdir(install_dir)
    gen_command = [sys.executable, meson_command, '--prefix', '/usr', '--libdir', 'lib', testdir, test_build_dir]\
        + unity_flags + backend_flags
    p = subprocess.Popen(gen_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (stdo, stde) = p.communicate()
    stdo = stdo.decode('utf-8')
    stde = stde.decode('utf-8')
    if not should_succeed:
        if p.returncode != 0:
            return ('', stdo, stde)
        return ('Test that should have failed succeeded', stdo, stde)
    if p.returncode != 0:
        return ('Generating the build system failed.', stdo, stde)
    if 'msbuild' in compile_commands[0]:
        sln_name = glob(os.path.join(test_build_dir, '*.sln'))[0]
        comp = compile_commands + [os.path.split(sln_name)[-1]]
    else:
        comp = compile_commands
    pc = subprocess.Popen(comp, cwd=test_build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o, e) = pc.communicate()
    stdo += o.decode('utf-8')
    stde += e.decode('utf-8')
    if pc.returncode != 0:
        return ('Compiling source code failed.', stdo, stde)
    pt = subprocess.Popen(test_commands, cwd=test_build_dir,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (o, e) = pt.communicate()
    stdo += o.decode('utf-8')
    stde += e.decode('utf-8')
    if pt.returncode != 0:
        return ('Running unit tests failed.', stdo, stde)
    if len(install_commands) == 0:
        print("Skipping install test")
        return ('', '', '')
    else:
        env = os.environ.copy()
        env['DESTDIR'] = install_dir
        pi = subprocess.Popen(install_commands, cwd=test_build_dir, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (o, e) = pi.communicate()
        stdo += o.decode('utf-8')
        stde += e.decode('utf-8')
        if pi.returncode != 0:
            return ('Running install failed.', stdo, stde)
        return (validate_install(testdir, install_dir), stdo, stde)

@nottest
def gather_tests(testdir):
    tests = [t.replace('\\', '/').split('/', 2)[2] for t in glob(os.path.join(testdir, '*'))]
    testlist = [(int(t.split()[0]), t) for t in tests]
    testlist.sort()
    tests = [os.path.join(testdir, t[1]) for t in testlist]
    return tests

@nottest
def check_file(fname):
    linenum = 1
    for line in open(fname, 'rb').readlines():
        if b'\t' in line:
            print("File %s contains a literal tab on line %d. Only spaces are permitted." % (fname, linenum))
            sys.exit(1)
        if b'\r' in line:
            print("File %s contains DOS line ending on line %d. Only unix-style line endings are permitted." % (fname, linenum))
            sys.exit(1)
        linenum += 1

@nottest
def check_format():
    for (root, _, files) in os.walk('.'):
        for file in files:
            if file.endswith('.py') or file.endswith('.build'):
                fullname = os.path.join(root, file)
                check_file(fullname)
@nottest
def generate_prebuilt_object():
    source = 'test cases/prebuilt object/1 basic/source.c'
    objectbase = 'test cases/prebuilt object/1 basic/prebuilt.'
    if shutil.which('cl'):
        objectfile = objectbase + 'obj'
        cmd = ['cl', '/nologo', '/Fo'+objectfile, '/c', source]
    else:
        if mesonlib.is_windows():
            objectfile = objectbase + 'obj'
        else:
            objectfile = objectbase + 'o'
        cmd = ['cc', '-c', source, '-o', objectfile]
    subprocess.check_call(cmd)
    return objectfile

def setup():
    global pbfile
    pbfile = generate_prebuilt_object()

def teardown():
    global pbfile
    if pbfile:
        os.unlink(pbfile)
        pbfile = None

@with_setup(setup, teardown)
def test_generator():
    setup_commands('MESON_BACKEND' in os.environ)
    script_dir = os.path.split(__file__)[0]
    if script_dir != '':
        os.chdir(script_dir)
    check_format()
    tests = []
    commontests = gather_tests('test cases/common')
    failtests = gather_tests('test cases/failing')
    objtests = gather_tests('test cases/prebuilt object')
    if mesonlib.is_linux():
        cpuid = platform.machine()
        if cpuid != 'x86_64' and cpuid != 'i386' and cpuid != 'i686':
            # Don't have a prebuilt object file for those so skip.
            objtests = []
    if mesonlib.is_osx():
        platformtests = gather_tests('test cases/osx')
    elif mesonlib.is_windows():
        platformtests = gather_tests('test cases/windows')
    else:
        platformtests = gather_tests('test cases/linuxlike')
    if not mesonlib.is_osx() and not mesonlib.is_windows():
        frameworktests = gather_tests('test cases/frameworks')
    else:
        frameworktests = []
    if not mesonlib.is_osx() and shutil.which('javac'):
        javatests = gather_tests('test cases/java')
    else:
        javatests = []
    if shutil.which('mcs'):
        cstests = gather_tests('test cases/csharp')
    else:
        cstests = []
    if shutil.which('valac'):
        valatests = gather_tests('test cases/vala')
    else:
        valatests = []
    if shutil.which('rustc'):
        rusttests = gather_tests('test cases/rust')
    else:
        rusttests = []
    if not mesonlib.is_windows():
        objctests = gather_tests('test cases/objc')
    else:
        objctests = []
    if shutil.which('gfortran'):
        fortrantests = gather_tests('test cases/fortran')
    else:
        fortrantests = []
    try:
        os.mkdir(test_build_dir)
    except OSError:
        pass
    try:
        os.mkdir(install_dir)
    except OSError:
        pass
    print('Running common tests.')
    tests += [tuple([x, True]) for x in commontests]
    print('Running failing tests.')
    tests += [tuple([x, False]) for x in failtests]
    if len(objtests) > 0:
        print('Running object inclusion tests.')
        tests += [tuple([x, True]) for x in objtests]
    else:
        print('No object inclusion tests.')
    if len(platformtests) > 0:
        print('Running platform dependent tests.')
        tests += [tuple([x, True]) for x in platformtests]
    else:
        print('No platform specific tests.')
    if len(frameworktests) > 0:
        print('Running framework tests.')
        tests += [tuple([x, True]) for x in frameworktests]
    else:
        print('No framework tests on this platform.')
    if len(javatests) > 0:
        print('Running java tests.')
        tests += [tuple([x, True]) for x in javatests]
    else:
        print('Not running Java tests.')
    if len(cstests) > 0:
        print('Running C# tests.')
        tests += [tuple([x, True]) for x in cstests]
    else:
        print('Not running C# tests.')
    if len(valatests) > 0:
        print('Running Vala tests.')
        tests += [tuple([x, True]) for x in valatests]
    else:
        print('Not running Vala tests.')
    if len(rusttests) > 0:
        print('Running Rust tests.')
        tests += [tuple([x, True]) for x in rusttests]
    else:
        print('Not running Rust tests.')
    if len(objctests) > 0:
        print('Running Objective C tests.')
        tests += [tuple([x, True]) for x in objctests]
    else:
        print('No Objective C tests on this platform.')
    if len(fortrantests) > 0:
        print('Running Fortran tests.')
        tests += [tuple([x, True]) for x in fortrantests]
    else:
        print('No Fortran tests on this platform.')
    for test in tests:
        f = partial(check, test[0], test[1])
        update_wrapper(f, check)
        f.description = test[0].replace('.', '_')
        test_generator.__name__ = f.description
        yield f

def check(testpath, should_succeed):
    (msg, stdo, stde) = run_test(testpath, should_succeed)
    print(stdo)
    print(stde, file=sys.stderr)
    assert msg == ''
