# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Red Hat, Inc

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import typing as T

from .. import mlog

if T.TYPE_CHECKING:
    from ..programs import ExternalProgram as Executable
    from typing_extensions import TypedDict

    class ModFiles(TypedDict):
        te: str
        if_: str
        fc: str

    class SupportFiles(TypedDict):
        m4support: T.List[str]
        header_interfaces: T.List[str]
        all_interfaces: str


parser = argparse.ArgumentParser(
    description="Python script for building SELinux policies.",
)
parser.add_argument("--output", required=True, help="Path to the output PP file.")
parser.add_argument("--te", required=True, help="Path to the Type Enforcement file.")
parser.add_argument("--if", dest='if_', help="Path to the Interface file.")
parser.add_argument("--fc", help="Path to the File Context file.")
parser.add_argument("--name", help="The name of the policy type to build for (e.g., `targeted`, `mls`).")

parser.add_argument("--mls", default=False, action="store_true", help="Enable MLS (Multi-Level Security).")
parser.add_argument("--ubac", default=False, action="store_true", help="Enable UBAC (User-Based Access Control).")
parser.add_argument("--type", default="standard", choices=['standard', 'mls', 'mcs'], help="Policy type.")
parser.add_argument("--distro", help="Enable distribution-specific policy (e.g., 'redhat').")
parser.add_argument("--direct-initrc", default=False, action="store_true", help="Enable direct sysadm daemon.")

parser.add_argument("--depfile", help="Path to a file where dependencies are stored.")
parser.add_argument("--private-dir", help="Path to a directory where all intermediate files are stored.")
parser.add_argument("--quiet", action="store_true", help="Suppress command echoing.")


class Builder:
    def __init__(self, args: argparse.Namespace) -> None:
        self.share_dir = "/usr/share/selinux/"
        self.etc_config = "/etc/selinux/config"
        self.private_dir = args.private_dir
        if self.private_dir is None:
            self._private_tmp_dir = tempfile.TemporaryDirectory(prefix="selinux-private-")
            self.private_dir = self._private_tmp_dir.name
        self.name = args.name if args.name else self._read_selinuxtype()
        self.mls = args.mls
        self.type = args.name if args.name else ('mls' if self.name == 'mls' else 'standard')
        self.distro = args.distro
        self.direct_initrc = args.direct_initrc
        self.ubac = args.ubac
        self.quiet = args.quiet

        self.header_dir = os.path.join(self.share_dir, "devel", "include")
        self._read_build_conf()

        self.support_files = self._find_support_files()
        self.m4 = find_program('m4', env_var='M4')
        self.checkmodule = find_program('checkmodule', env_var='CHECKMODULE')
        self.semod_pkg = find_program('semodule_package', env_var='SEMOD_PKG')

    def build(self, output: str, te: str, if_: str, fc: str, depfile: str) -> None:
        mod_files = self._input_files(te, if_, fc)
        self._populate_all_interfaces(mod_files['if_'])
        self._build_mod(output, mod_files)

        if depfile:
            self._write_depfile(depfile, output, mod_files)

    def _write_depfile(self, depfile: str, output: str, mod_files: "ModFiles") -> None:
        mlog.notice(f"Generating dependency file {depfile}")
        build_conf = makefile_quote_space(self._build_conf())
        etc_conf = makefile_quote_space(self.etc_config)
        all_support_files: T.List[str] = []
        for val in self.support_files.values():
            if isinstance(val, list):
                all_support_files.extend(val)
            elif isinstance(val, str):
                all_support_files.append(val)
        all_support_files = [makefile_quote_space(e) for e in all_support_files]
        mod_files_list = [makefile_quote_space(str(e)) for e in mod_files.values()]
        with open(depfile, 'w', encoding='utf-8') as f:
            f.write(f"{output}: {' '.join(mod_files_list)} {etc_conf} {build_conf} {' '.join(all_support_files)}\n")

    def _input_files(self, te: str, if_: str, fc: str) -> "ModFiles":
        """Creates temporary empty .if and .fc files if they are missing."""
        mod_files: "ModFiles" = {'te': te, 'if_': if_, 'fc': fc}
        base_name = te.replace(".te", "")
        if not if_:
            if_ = f"{base_name}.if"
            mlog.notice(f"Creating {if_}")
            if_ = os.path.join(self.private_dir, if_)
            with open(if_, "w", encoding='utf-8') as f:
                summary_name = os.path.basename(base_name)
                f.write(f"## <summary>{summary_name}</summary>\n")
            mod_files['if_'] = if_
        if not fc:
            fc = f"{base_name}.fc"
            mlog.notice(f"Creating empty {fc}")
            fc = os.path.join(self.private_dir, fc)
            open(fc, "w", encoding='utf-8').close()
            mod_files['fc'] = fc
        return mod_files

    def _populate_all_interfaces(self, if_: str) -> None:
        inputs = self.support_files['m4support'] + self.support_files['header_interfaces'] + [if_]
        output = os.path.join(self.private_dir, "all_interfaces.conf")
        with open(output, 'w', encoding='utf-8') as out_file:
            with tempfile.NamedTemporaryFile(mode='w+t', delete=True, prefix="selinux-m4-iferror", encoding='utf-8') as tmp_file:
                tmp_file.write("ifdef(`__if_error',`m4exit(1)')\n")
                m4_cmd = [self.m4.get_path()] + inputs + [tmp_file.name]
                result = run_command(m4_cmd, self.quiet)
                out = result.stdout.replace('dollarsstar', '*')
                out_file.write('divert(-1)\n')
                out_file.write(out)
                out_file.write('divert\n')
        self.support_files['all_interfaces'] = output

    def _build_mod(self, pp_output: str, mod_files: "ModFiles") -> None:
        mlog.notice(f"Building module {pp_output}")

        mod_prefix = os.path.splitext(mod_files['te'])[0]
        mod_name = os.path.basename(mod_prefix)
        m4_args = self._m4_args()

        # pre-process TE
        tmp_output = os.path.join(self.private_dir, mod_name + ".tmp")
        input_files = self.support_files['m4support'] + [self.support_files['all_interfaces'], mod_files['te']]
        m4_cmd = [self.m4.get_path(), '-s'] + m4_args + input_files
        run_command(m4_cmd, stdout_file=tmp_output, quiet=self.quiet)

        # build .mod
        mod_output = os.path.join(self.private_dir, mod_name + ".mod")
        checkmodule_cmd = [self.checkmodule.get_path()] + self._checkmodule_args() + ['-m', tmp_output, '-o', mod_output]
        run_command(checkmodule_cmd, self.quiet)

        # build .mod.fc
        mod_fc_output = os.path.join(self.private_dir, mod_name + ".mod.fc")
        input_files = self.support_files['m4support'] + [mod_files['fc']]
        m4_cmd = [self.m4.get_path()] + m4_args + input_files
        run_command(m4_cmd, stdout_file=mod_fc_output, quiet=self.quiet)

        # build .pp
        semod_pkg_cmd = [self.semod_pkg.get_path(), '-o', pp_output, '-m', mod_output, '-f', mod_fc_output]
        run_command(semod_pkg_cmd, self.quiet)

    def _read_selinuxtype(self) -> str:
        """Reads /etc/selinux/config to find SELINUXTYPE."""
        try:
            with open(self.etc_config, encoding='utf-8') as f:
                for line in f:
                    match = re.match(r"^\s*SELINUXTYPE\s*=\s*(\S+)", line)
                    if match:
                        return match.group(1)
        except FileNotFoundError:
            mlog.warning(f"{self.etc_config} not found. Using 'default' SELINUXTYPE.")
            return "default"
        return "default"

    def _build_conf(self) -> str:
        return os.path.join(self.header_dir, "build.conf")

    def _read_build_conf(self) -> None:
        build_conf = self._build_conf()
        with open(build_conf, 'r', encoding='utf-8') as f:
            build_vars: T.Dict[str, str] = {k: v for k, v in {
                'TYPE': self.type,
                'NAME': self.name,
                'DISTRO': self.distro,
                'DIRECT_INITRC': 'y' if self.direct_initrc else 'n'
            }.items() if v is not None}
            build_vars = parse_makefile_variables(f.read(), build_vars)

            self.type = build_vars.get('TYPE', 'standard')
            self.name = build_vars['NAME']
            self.distro = build_vars.get('DISTRO')
            self.direct_initrc = build_vars.get('DIRECT_INITRC', 'n') == 'y'
            self.ubac = build_vars.get('UBAC', 'n') == 'y'
            self.mls_sens = build_vars.get('MLS_SENS', '16')
            self.mls_cats = build_vars.get('MLS_CATS', '1024')
            self.mcs_cats = build_vars.get('MCS_CATS', '1024')

    def _find_support_files(self) -> "SupportFiles":
        files: T.Dict[str, T.Union[str, T.List[str]]] = {}
        files['m4support'] = sorted(glob.glob(os.path.join(self.header_dir, "support", "*.spt")))

        header_layers = [d for d in glob.glob(os.path.join(self.header_dir, "*")) if os.path.isdir(d) and 'support' not in d]
        header_interfaces: T.List[str] = []
        for layer in header_layers:
            header_interfaces.extend(glob.glob(os.path.join(layer, "*.if")))
        files['header_interfaces'] = sorted(header_interfaces)

        return T.cast('SupportFiles', files)

    def _checkmodule_args(self) -> T.List[str]:
        return ['-M'] if self.type in {'mls', 'mcs'} else []

    def _m4_args(self) -> T.List[str]:
        m4_args: T.List[str] = []
        if self.type == 'mls':
            m4_args.extend(['-D', 'enable_mls'])
        elif self.type == 'mcs':
            m4_args.extend(['-D', 'enable_mcs'])
        if self.distro:
            m4_args.extend(['-D', f'distro_{self.distro}'])
        if self.direct_initrc:
            m4_args.extend(['-D', 'direct_sysadm_daemon'])
        if self.ubac:
            m4_args.extend(['-D', 'enable_ubac'])

        m4_args.extend(['-D', 'hide_broken_symptoms'])
        m4_args.extend(['-D', f'mls_num_sens={self.mls_sens}'])
        m4_args.extend(['-D', f'mls_num_cats={self.mls_cats}'])
        m4_args.extend(['-D', f'mcs_num_cats={self.mcs_cats}'])
        return m4_args

    def __str__(self) -> str:
        config_summary = [
            f"  Policy Name:        {self.name}",
            f"  Policy Type:        {self.type}",
            f"  Distro:             {self.distro if self.distro else '[none]'}",
            f"  Direct InitRC:      {self.direct_initrc}",
            f"  MLS Enabled (arg):  {self.mls}", # Reflects the direct --mls argument
            f"  UBAC Enabled:       {self.ubac}",
            f"  MLS Sensitivities:  {self.mls_sens}",
            f"  MLS Categories:     {self.mls_cats}",
            f"  MCS Categories:     {self.mcs_cats}",
            f"  Share Directory:    {self.share_dir}",
            f"  Header Directory:   {self.header_dir}",
            f"  Private Directory:  {self.private_dir}"
        ]
        return "\n".join(config_summary)


def run_command(cmd: T.List[str], quiet: bool = False, stdout_file: T.Optional[str] = None) -> subprocess.CompletedProcess:
    """Executes a command, printing it first unless in quiet mode."""
    if not quiet:
        printable_cmd = ' '.join(cmd)
        if stdout_file:
            printable_cmd += f" > {stdout_file}"
        mlog.notice(f"Executing: {printable_cmd}")

    try:
        if stdout_file:
            with open(stdout_file, "w", encoding='utf-8') as f_out:
                result = subprocess.run(cmd, check=True, text=True, stdout=f_out, stderr=subprocess.PIPE, encoding='utf-8')
        else:
            result = subprocess.run(cmd, check=True, text=True, capture_output=True, encoding='utf-8')
    except FileNotFoundError as e:
        mlog.error(f"Error: Command not found: {e.filename}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        mlog.error(f"Error executing command: {' '.join(cmd)}")
        mlog.error(f"Return code: {e.returncode}")
        if e.stdout:
            mlog.error(f"Stdout:\n{e.stdout}")
        if e.stderr:
            mlog.error(f"Stderr:\n{e.stderr}")
        sys.exit(1)
    return result


def parse_makefile_variables(content: str, variables: T.Optional[T.Dict[str, str]]) -> T.Dict[str, str]:
    """
    Parses a Makefile to extract variable assignments.

    This function reads a file line by line and uses a regular expression
    to find variable declarations. It correctly interprets the logic for
    standard (`=`, `:=`), conditional (`?=`), and override assignments.

    Args:
        file_path (str): The path to the Makefile or file with variables.

    Returns:
        dict: A dictionary containing the parsed variable names and their values.
    """
    if variables is None:
        variables = {}

    # Regex to capture the variable name, assignment operator, and value.
    # It correctly handles optional 'override', different operators,
    # and strips trailing whitespace and comments.
    var_regex = re.compile(
        r"^\s*(?:override\s+)?(?P<name>[a-zA-Z0-9_-]+)\s*(?P<operator>[:?]?=)\s*(?P<value>.*?)\s*(?:#.*)?$"
    )

    for line in content.splitlines():
        match = var_regex.match(line)
        if match:
            data = match.groupdict()
            name = data['name']
            operator = data['operator']
            value = data['value'].strip()

            # For conditional assignment ('?='), only set the variable
            # if it has not been defined yet.
            if operator == '?=':
                if name not in variables:
                    variables[name] = value
            # For regular ('=') and simple (':=') assignments,
            # set or overwrite the variable.
            else:
                variables[name] = value
    return variables


def makefile_quote_space(val: str) -> str:
    return val.replace(" ", "\\ ")


def find_program(name: str, cli_arg: T.Optional[str] = None, env_var: T.Optional[str] = None) -> "Executable":
    from ..programs import ExternalProgram as Executable
    if cli_arg:
        if os.path.isfile(cli_arg) and os.access(cli_arg, os.X_OK):
            return Executable(cli_arg)
        mlog.error(f"{cli_arg} is not an executable file")
        sys.exit(1)
    if env_var and env_var in os.environ:
        path = os.environ[env_var]
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return Executable(path)
        mlog.error(f"{env_var}={path} is not executable")
        sys.exit(1)
    path = shutil.which(name)
    if path:
        return Executable(path)
    mlog.error(f"Required program '{name}' not found in PATH")
    sys.exit(1)


def run(args: T.List[str]) -> int:
    options = parser.parse_args(args)
    if options.quiet:
        mlog.set_quiet()
    mlog.debug(f"Options: {options}, pwd: {os.getcwd()}")
    builder = Builder(options)
    builder.build(options.output, options.te, options.if_, options.fc, options.depfile)
    mlog.notice("Done")
    return 0
