# Copyright 2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module for freedesktop related standards."""

import argparse
import configparser
import json
import os
import sys
import typing as T
import xml.etree.ElementTree as et

# These must be imported as absolute imports to make the __main__ thing work
from mesonbuild.build import Executable, CustomTarget, EnvironmentVariables
from mesonbuild.interpreter import Test, CustomTargetHolder
from mesonbuild.interpreterbase import permittedKwargs
from mesonbuild.mesonlib import (
    FileMode,
    MachineChoice,
    MesonException,
    listify,
    stringlistify,
    unholder,
)
from mesonbuild.modules import ExtensionModule, ModuleReturnValue, python

if T.TYPE_CHECKING:
    # This can be relative because they're only read by mypy
    from ..interpreter import ModuleState, ExecutableHolder
    from ..interpreterbase import Disabler

    _T = T.TypeVar('_T')


class FDOConfigParser(configparser.RawConfigParser):

    """Special case config parser that doesn't muck with capitaliation."""

    def __init__(self, *args, **kwargs):
        # Turn off interpolation, it inteferes with the .desktop file's % syntax.
        super().__init__(*args, interpolation=None, **kwargs)

    def optionxform(self, value: '_T') -> '_T':
        return value


def optional_string_arg(kwargs: T.Dict[str, T.Any], kkey: str,
                        values: T.Dict[str, T.Union[str, T.Dict[str, str]]], vkey: str, *,
                        fallback: T.Optional[str] = None) -> None:
    value = kwargs.get(kkey, fallback)
    if value is not None:
        if not isinstance(value, str):
            raise MesonException('"{}" must be a string if defined'.format(kkey))
        values[vkey] = value


def optional_bool_arg(kwargs: T.Dict[str, T.Any], kkey: str,
                      values: T.Dict[str, T.Union[str, T.Dict[str, str]]], vkey: str, *,
                      fallback: T.Optional[bool] = None) -> None:
    value = kwargs.get(kkey, fallback)
    if value is not None:
        if not isinstance(value, bool):
            raise MesonException('"{}" must be a bool if defined'.format(kkey))
        values[vkey] = str(value).lower()


def optional_list_arg(kwargs: T.Dict[str, T.Any], kkey: str,
                      values: T.Dict[str, T.Union[str, T.Dict[str, str]]], vkey: str) -> None:
    value = stringlistify(kwargs.get(kkey, []))
    if value:
        values[vkey] = ';'.join(value)


def generate_desktop_file(cmdline: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('json')
    parser.add_argument('output')
    args = parser.parse_args(cmdline)

    commands = json.loads(args.json)
    # The escaping has to be done in the generator function, as JSON doesn't
    # like the escaping that desktop files use
    commands['main']['Exec'] = '"{}"'.format(
        ' '.join(escape_exec_arg(c) for c in commands['main']['Exec']))

    config = FDOConfigParser()
    config['Desktop Entry'] = commands['main']
    for name, action in commands['actions'].items():
        action['Exec'] = '"{}"'.format(
            ' '.join(escape_exec_arg(c) for c in action['Exec']))
        config['Desktop Action {}'.format(name)] = action

    with open(args.output, 'w') as f:
        config.write(f)

    return 0


def escape_exec_arg(arg: str) -> str:
    final = []  # type: T.List[str]
    for c in arg:
        if c in {'`', '$', '\\'}:
            final.append('\\')
        final.append(c)
    return "{}".format(''.join(final))


def subelem_text(parent: et.Element, tag: str, text: str, **kwargs: str) -> et.Element:
    e = et.SubElement(parent, tag, **kwargs)
    e.text = text
    return e


def generate_appstream_file(cmdline: T.List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('json')
    parser.add_argument('output')
    args = parser.parse_args(cmdline)

    data = json.loads(args.json)

    root = et.Element('component', type='desktop-application')
    subelem_text(root, 'id', data['fqname'])
    subelem_text(root, 'name', data['project_name'])

    for l in data['project_licenses']:
        subelem_text(root, 'project_license', l)

    subelem_text(root, 'metadata_license', data['metadata_license'])

    if data['summary']:
        subelem_text(root, 'summary', data['summary'])

    if data['description']:
        desc = et.SubElement(root, 'description')
        desc.append(et.fromstring(data['description']))

    if data['launchable']:
        subelem_text(root, 'launchable', data['launchable'], type='desktop-id')

    tree = et.ElementTree(root)
    with open(args.output, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)

    return 0


class FreedesktopModule(ExtensionModule):

    @permittedKwargs({'name', 'arguments', 'generic_name', 'icon',
                      'categories', 'actions', 'install_name', 'mimetype', 'comment', 'dbus',
                      'no_display', 'implements', 'keywords', 'startup_notify',
                      'startup_wm_class', 'extra_args', 'test_target'})
    def desktop_file(self, state: 'ModuleState',
                     args: T.Tuple[T.Union['ExecutableHolder', 'Disabler']],
                     kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        if len(args) != 1:
            raise MesonException('Only one positinal argument allowed.')

        exe = args[0].held_object  # type: Executable
        if not isinstance(exe, Executable):
            raise MesonException('First argument must be an Executable')
        test = kwargs.get('test_target', False)
        if not isinstance(test, bool):
            raise MesonException('"test_target" must be a bool if defined')

        values = {}  # type: T.Dict[str, T.Union[str, T.Dict[str, str]]]

        full_exe = os.path.join(exe.get_install_dir(state.environment)[0][0], exe.name)
        arguments = stringlistify(kwargs.get('arguments', []))

        optional_string_arg(kwargs, 'name', values, 'Name', fallback=exe.name)
        values['Terminal'] = str(not exe.gui_app).lower()
        values['Exec'] = [full_exe, *arguments]
        values['TryExec'] = full_exe
        values['Type'] = 'Application'
        values['Version'] = '1.1'
        optional_string_arg(kwargs, 'comment', values, 'Comment')
        optional_string_arg(kwargs, 'generic_name', values, 'GenericName')
        optional_string_arg(kwargs, 'icon', values, 'Icon')
        optional_string_arg(kwargs, 'startup_wm_class', values, 'StartupWMClass')
        optional_list_arg(kwargs, 'categories', values, 'Categories')
        optional_list_arg(kwargs, 'mimetype', values, 'MimeType')
        optional_list_arg(kwargs, 'not_show_in', values, 'NotShowIn')
        optional_list_arg(kwargs, 'only_show_in', values, 'OnlyShowIn')
        optional_list_arg(kwargs, 'implements', values, 'Implements')
        optional_list_arg(kwargs, 'keywords', values, 'Keywords')
        optional_bool_arg(kwargs, 'dbus', values,  'DBusActivatable')
        optional_bool_arg(kwargs, 'no_display', values,  'NoDisplay')
        optional_bool_arg(kwargs, 'startup_notify', values,  'StartupNotify')

        extra_args = kwargs.get('extra_args', {})
        for k, v in extra_args.items():
            if not k.startswith('X-'):
                raise MesonException('extra_args keys must start with "X-"')
            if isinstance(v, str):
                kwargs[k] = v
            elif isinstance(v, bool):
                kwargs[k] = str(v).lower()
            else:
                kwargs[k] = ';'.join(stringlistify(v))

        all_actions = {}
        actions = listify(kwargs.get('actions', []))
        if actions:
            for action in actions:
                if not isinstance(action, dict):
                    raise MesonException('"actions" must be a list of dicts if defined.')
                if 'action' not in action:
                    raise MesonException('missing required "action" entry in action "{}"'.format(action))
                if not isinstance(action['action'], str):
                    raise MesonException("Action key of actions must be a string")
                if 'name' not in action:
                    raise MesonException('missing required "name" entry in action "{}"'.format(action))
                if not isinstance(action['name'], str):
                    raise MesonException("Name key of actions must be a string")

                avalues = {}
                avalues['Name'] = action['name']

                exec_ = stringlistify(action['exec'])
                avalues['Exec'] =  [full_exe, *exec_]

                optional_string_arg(action, 'icon', avalues, 'Icon')

                all_actions[action['action']] = avalues

        install_name = kwargs.get('install_name', values['Name'])
        if not isinstance(install_name, str):
            raise MesonException('install_name must be a string if provided')
        if install_name.endswith('.desktop'):
            raise MesonException('install_name must not include the .desktop '
                                 'file extension.')

        values['Actions'] = ';'.join(a['action'] for a in actions)

        root = {'main': values, 'actions': all_actions}

        py = python.PythonModule(self.interpreter).find_installation(
            self.interpreter, state, ['python3'], {})
        ct = CustomTarget(
            'meson-freedesktop-{}'.format(install_name),
            state.environment.get_scratch_dir(),
            self.interpreter.subproject,
            {
                'output': '{}.desktop'.format(install_name),
                'command': [
                    py, __file__, 'desktop_file',
                    json.dumps(root), '@OUTPUT@',
                ],
                'install': exe.should_install(),
                'install_dir': os.path.join(state.environment.get_datadir(), 'applications'),
                'install_mode': FileMode('rw-r--r--'),
                'depends': args[0],
            },
            internal_target=True,
        )

        new_objs = [ct]

        if test:
            validator = self.interpreter.find_program_impl(
                ['desktop-file-validate'], required=False, for_machine=MachineChoice.BUILD)
            tt = Test(
                'validate meson-freedesktop-{}'.format(install_name),
                self.interpreter.subproject,
                suite=['freedesktop-module'],
                exe=validator.held_object,
                depends=[],
                is_parallel=True,
                cmd_args=[ct],
                env=EnvironmentVariables(),
                should_fail=False,
                timeout=30,
                workdir=None,
                protocol='exitcode',
                priority=0,
            )
            new_objs.append(tt)

        return ModuleReturnValue(ct, new_objs)

    @permittedKwargs({'metadata_license', 'summary', 'description',
                      'desktop_file', 'test_target'})
    def appstream(self, state: 'ModuleState',
                  args: T.Tuple[str, str],
                  kwargs: T.Dict[str, T.Any]) -> ModuleReturnValue:
        if len(args) != 2:
            raise MesonException('appstream method requires exactly two positional arguments.')

        data = {}  # type: T.Dict[str, object]

        domain, name = args
        if not isinstance(domain, str):
            raise MesonException('Positional argument 0 (domain) must be a string.')
        if not isinstance(name, str):
            raise MesonException('Positional argument 0 (domain) must be a string.')
        data['fqname'] = '.'.join([domain, name])
        data['project_name'] = self.interpreter.build.project_name
        data['project_licenses'] = stringlistify(self.interpreter.build.dep_manifest[self.interpreter.active_projectname]['license'])
        data['summary'] = kwargs.get('summary')
        if data['summary'] is not None and not isinstance(data['summary'], str):
            raise MesonException('Summary must be a string if provided.')
        data['metadata_license'] = kwargs.get('metadata_license', 'CC0-1.0')
        if data['metadata_license'] is not None and not isinstance(data['metadata_license'], str):
            raise MesonException('metadata_license must be a string if provided.')
        data['description'] = kwargs.get('description')
        if data['description']:
            if not isinstance(data['description'], str):
                raise MesonException('description must be a string if provided.')
            try:
                et.fromstring(data['description'])
            except et.ParseError:
                raise MesonException('Improperly formatted xml in appstream description.')

        data['launchable'] = None
        d = kwargs.get('desktop_file')  # type: T.Optional[T.Union[CustomTarget, CustomTargetHolder]]
        if d:
            assert isinstance(d, CustomTargetHolder)
            d = unholder(d)
            if not isinstance(d, CustomTarget):
                raise MesonException('desktop_file must be an object returned by freedesktop.desktop_file.')
            data['launchable'] = d.name
        assert d is None or isinstance(d, CustomTarget)

        test = kwargs.get('test_target', False)
        if not isinstance(test, bool):
            raise MesonException('test_target must be a boolean')

        install_name = '{}.{}.metainfo.xml'.format(domain, name)

        py = python.PythonModule(self.interpreter).find_installation(
            self.interpreter, state, ['python3'], {})
        ct = CustomTarget(
            'meson-freedesktop-{}'.format(install_name),
            state.environment.get_scratch_dir(),
            self.interpreter.subproject,
            {
                'output': install_name,
                'command': [
                    py, __file__, 'appstream_file',
                    json.dumps(data), '@OUTPUT@',
                ],
                'install': d.install if d is not None else True,
                'install_dir': os.path.join(state.environment.get_datadir(), 'metainfo'),
                'install_mode': FileMode('rw-r--r--'),
                'depends': [d],
            },
            internal_target=True,
        )

        new_objs = [ct]

        if test:
            validator = self.interpreter.find_program_impl(
                ['appstreamcli'], required=False, for_machine=MachineChoice.BUILD)
            tt = Test(
                'validate meson-freedesktop-{}'.format(install_name),
                self.interpreter.subproject,
                suite=['freedesktop-module'],
                exe=validator.held_object,
                depends=[],
                is_parallel=True,
                cmd_args=['validate', '--no-net', '--pedantic', ct],
                env=EnvironmentVariables(),
                should_fail=False,
                timeout=30,
                workdir=None,
                protocol='exitcode',
                priority=0,
            )
            new_objs.append(tt)

        return ModuleReturnValue(ct, new_objs)


def initialize(*args, **kwargs) -> FreedesktopModule:
    return FreedesktopModule(*args, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode')
    args, remaining = parser.parse_known_args()

    if args.mode == 'desktop_file':
        callable_ = generate_desktop_file
    elif args.mode == 'appstream_file':
        callable_ = generate_appstream_file

    sys.exit(callable_(remaining))
