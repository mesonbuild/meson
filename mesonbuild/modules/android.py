# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026  Florian Leander Singer <sp1rit@disroot.org>

import typing as T
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from . import ExtensionModule, ModuleReturnValue, ModuleInfo
from .. import build
from .. import mlog
from ..build import CustomTarget, Jar
from ..interpreter.type_checking import INSTALL_KW, INSTALL_DIR_KW, INSTALL_TAG_KW, NoneType
from ..interpreterbase import FeatureNew
from ..interpreterbase.decorators import ContainerTypeInfo, KwargInfo, typed_kwargs, typed_pos_args
from ..mesonlib import File, MachineChoice, MesonException

if T.TYPE_CHECKING:
    from pathlib import Path
    from typing_extensions import TypedDict

    from . import ModuleState
    from ..build import GeneratedTypes
    from ..compilers import Compiler
    from ..interpreter.interpreter import Interpreter
    from ..programs import Program

APK_SOURCES_VARARGS = (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList, Jar)
if T.TYPE_CHECKING:
    ApkSourcesType = T.List[T.Union[str, File, GeneratedTypes, Jar]]

    class GenerateApk(TypedDict):
        app_id: T.Optional[str]
        target_sdk: T.Optional[int]
        min_sdk: T.Optional[int]
        resources: T.List[T.Union[str, File, GeneratedTypes]]
        install: bool
        install_dir: T.Optional[str]
        install_tag: T.Optional[str]

@dataclass
class JavaLinkingTools:
    jmod: 'Program'
    jlink: 'Program'

@dataclass
class JavaTools:
    java_home: 'Path'
    javac: 'Compiler'
    linking: T.Optional[JavaLinkingTools]

@dataclass
class AndroidTools:
    aapt2: 'Program'
    d8: 'Program'
    zipalign: 'Program'
    apksigner: 'Program'


class AndroidModule(ExtensionModule):

    INFO = ModuleInfo('android')

    # TODO: maybe get from property?
    android_home = '/home/florian/Android/Sdk'

    def __init__(self, interpreter: 'Interpreter'):
        super().__init__(interpreter)
        self.methods.update({
            'generate_apk': self.generate_apk,
        })

        self.java_tools: T.Optional[JavaTools] = None
        self.android_tools: T.Optional[AndroidTools] = None
        self.android_images: T.Dict[int, T.Tuple[str, CustomTarget]] = {}

    def _get_java_linking_tools(self, state: 'ModuleState', java_home: 'Path') -> JavaLinkingTools:
        jmod = state.find_program('jmod', search_dirs=[str(java_home.joinpath('bin'))])
        jlink = state.find_program('jlink', search_dirs=[str(java_home.joinpath('bin'))])
        return JavaLinkingTools(jmod, jlink)

    def get_java_tools(self, state: 'ModuleState', linking: bool) -> JavaTools:
        if self.java_tools is not None:
            if not linking or self.java_tools.linking is not None:
                return self.java_tools
            else:
                self.java_tools.linking = self._get_java_linking_tools(state, self.java_tools.java_home)
                return self.java_tools

        if 'java' not in state.environment.coredata.compilers[MachineChoice.BUILD]:
            raise MesonException('Unable to find java compiler in project')
        javac = state.environment.coredata.compilers[MachineChoice.BUILD]['java']
        java_home = state.environment.properties[MachineChoice.BUILD].get_java_home()
        if java_home is None:
            raise MesonException('TODO: factor the complex java_home determination code from dependencies.dev into a shared function')
        linking_tools = self._get_java_linking_tools(state, java_home) if linking else None
        self.java_tools = JavaTools(java_home, javac, linking_tools)
        return self.java_tools

    def get_android_tools(self, state: 'ModuleState') -> AndroidTools:
        if self.android_tools is not None:
            return self.android_tools

        aapt2 = state.find_program('aapt2')
        d8 = state.find_program('d8')
        zipalign = state.find_program('zipalign')
        apksigner = state.find_program('apksigner')
        self.android_tools = AndroidTools(aapt2, d8, zipalign, apksigner)
        return self.android_tools

    # Processes a Jar containing the system module classes into a JDK
    # Image, for use via the --system option of javac and other
    # Java-related tools.
    #
    # As per the discussion in b/154357088, the input for this process
    # is, properly, the core-for-system-modules.jar included starting in
    # SDK 30. The steps taken to transform the Jar are discussed in
    # b/63986449.
    #
    # The equivalent AGP implementation is located at
    # https://android.googlesource.com/platform/tools/base/+/mirror-goog-studio-main/build-system/gradle-core/src/main/java/com/android/build/gradle/internal/dependency/JdkImageTransformDelegate.kt
    def generate_android_image(self, state: 'ModuleState', sdk: int) -> T.List[CustomTarget]:
        # core-for-system-modules.jar seem to be available since either SDK 30 or 31 (conflicting reports)
        assert sdk >= 31

        tools = self.get_java_tools(state, True)

        imgtgt = f'android{sdk}_image'

        work_dir = os.path.join(state.environment.private_dir, imgtgt)
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(os.path.join(work_dir, 'jmod'), exist_ok=True)

        system_core_jar_path = os.path.join(self.android_home, 'platforms', f'android-{sdk}', 'core-for-system-modules.jar')

        module_info_java = CustomTarget(
            'module-info.java',
            work_dir,
            state.subproject,
            state.environment,
            [
                *state.environment.get_build_command(), '--internal',
                'android', 'modinfo-generate',
                '@OUTPUT@', '@INPUT@', 'java.base'
            ],
            [system_core_jar_path],
            ['module-info.java']
        )

        module_info_cls = CustomTarget(
            'module-info.class',
            work_dir,
            state.subproject,
            state.environment,
            [*tools.javac.exelist, '--system=none', f'--patch-module=java.base={system_core_jar_path}', '-d', work_dir, '@INPUT@'],
            [module_info_java],
            ['module-info.class']
        )

        module_jar = CustomTarget(
            'module.jar',
            work_dir,
            state.subproject,
            state.environment,
            [
                *state.environment.get_build_command(), '--internal',
                'android', 'zipmerge',
                '@OUTPUT@', '@INPUT@'
            ],
            [system_core_jar_path, module_info_cls],
            ['module.jar']
        )

        jlink_version = tools.linking.jlink.get_version().split('.')[0]

        jmod = CustomTarget(
            'java.base.jmod',
            os.path.join(work_dir, 'jmod'),
            state.subproject,
            state.environment,
            [
                *state.environment.get_build_command(), '--internal',
                'android', 'jmod', '@OUTPUT@',
                tools.linking.jmod, 'create',
                '--module-version', jlink_version,
                # --target-platform android was replaced with
                # LINUX-OTHER to be compatible with JDK 21+ b/294137077
                '--target-platform', 'LINUX-OTHER',
                '--class-path', '@INPUT@'
            ],
            [module_jar],
            ['java.base.jmod']
        )

        jimg = CustomTarget(
            'image',
            work_dir,
            state.subproject,
            state.environment,
            [
                *state.environment.get_build_command(), '--internal',
                'android', 'jlink', os.path.join(work_dir, 'image'), os.path.join(tools.java_home, 'lib', 'jrt-fs.jar'),
                tools.linking.jlink,
                '--module-path', os.path.join(work_dir, 'jmod'),
                '--add-modules', 'java.base',
                '--disable-plugin', 'system-modules'
            ],
            [jmod],
            ['image.tgt']
        )

        self.android_images[sdk] = (os.path.join(work_dir, 'image'), jimg)
        return [module_info_java, module_info_cls, module_jar, jmod, jimg]

    @FeatureNew('android.generate_apk', '1.11.0')
    @typed_pos_args(
        'android.generate_apk',
        (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList),
        varargs=APK_SOURCES_VARARGS
    )
    @typed_kwargs(
        'android.generate_apk',
        KwargInfo('app_id', (str, NoneType)),
        KwargInfo('target_sdk', (int, NoneType)),
        KwargInfo('min_sdk', (int, NoneType)),
        KwargInfo('resources', ContainerTypeInfo(list, (str, File, build.CustomTarget, build.CustomTargetIndex, build.GeneratedList)), listify=True, default=[]),
        INSTALL_KW,
        INSTALL_DIR_KW,
        INSTALL_TAG_KW,
    )
    def generate_apk(self, state: 'ModuleState',
                     args: T.Tuple[T.Union[str, File, 'GeneratedTypes'], 'ApkSourcesType'],
                     kwargs: 'GenerateApk') -> ModuleReturnValue:
        manifest_file, sources = args

        if isinstance(manifest_file, str):
            manifest_file = File.from_source_file(state.environment.source_dir, state.subdir, manifest_file)

        tgts: T.List[build.Target] = []

        app_id = kwargs['app_id']
        manifest_src = manifest_file
        if app_id is not None:
            work_dir = os.path.join(state.subdir, f'{app_id}.p')
            os.makedirs(os.path.join(state.environment.get_build_dir(), work_dir), exist_ok=True)

            manifest_src = CustomTarget(
                'AndroidManifest.xml',
                work_dir,
                state.subproject,
                state.environment,
                [
                    *state.environment.get_build_command(), '--internal',
                    'android', 'manifest-rewriter', '@INPUT@',
                    '--output', '@OUTPUT@',
                    '--appid', app_id
                ],
                [manifest_file],
                ['AndroidManifest.xml']
            )
            tgts.append(manifest_src)
        else:
            if not isinstance(manifest_file, File):
                raise MesonException('app_id is required if manifest is not a file')
            manifest = ET.parse(manifest_file.absolute_path(state.environment.source_dir, state.environment.build_dir))
            mf_root = manifest.getroot()
            if mf_root is None or mf_root.tag != 'manifest':
                raise MesonException(f'Manifest {manifest_file} is not a valid android manifest')
            app_id = mf_root.get('package')
            if app_id is None:
                raise MesonException('app_id is required if not specified in the manifest')

            work_dir = os.path.join(state.subdir, f'{app_id}.p')
            os.makedirs(os.path.join(state.environment.get_build_dir(), work_dir), exist_ok=True)

        target_sdk = kwargs['target_sdk']
        if target_sdk is None:
            raise MesonException('TODO: pick latest version from $ANDROID_HOME/platforms/')
        min_sdk = kwargs['min_sdk']
        if min_sdk is None:
            raise MesonException('TODO: determine min version from C compiler name')

        javac_args: T.List[str] = []
        javac_tgt_deps: T.List[CustomTarget] = []

        if target_sdk >= 36:
            # Starting with SDK 36, Android Studio defaults to Java 11,
            # as newer JDKs have deprecated support for Java 8 source &
            # target compatability. As such we'll need to pass java a
            # 'system image' describing java.base, which we'll have to
            # construct first.
            # Should the Java 8 deprecation become an actual problem for
            # us, I *belive* we could use Java 11 starting with SDK 30
            # or 31, as those are this first SDKs shipping the resources
            # needed to create the system image.
            if target_sdk not in self.android_images:
                tgts.extend(self.generate_android_image(state, target_sdk))
            img, dep = self.android_images[target_sdk]
            javac_args += ['-source', '11', '-target', '11', '--system', img]
            javac_tgt_deps.append(dep)
        else:
            javac_args += ['-source', '8', '-target', '8']

        tools = self.get_android_tools(state)

        if kwargs['resources']:
            resources = CustomTarget(
                'resources.zip',
                work_dir,
                state.subproject,
                state.environment,
                [
                    tools.aapt2, 'compile',
                    '-o', '@OUTPUT@',
                    '@INPUT@'
                ],
                self.interpreter.source_strings_to_files(kwargs['resources']),
                ['resources.zip']
            )
            tgts.append(resources)
        else:
            resources = None

        android_platform_jar = os.path.join(self.android_home, 'platforms', f'android-{target_sdk}', 'android.jar')

        container_apk, container_res = container_tgt = CustomTarget(
            'container.apk',
            work_dir,
            state.subproject,
            state.environment,
            T.cast(T.List[T.Union[str, 'Program']], [
                tools.aapt2, 'link',
                '-o', '@OUTPUT0@',
                '--min-sdk-version', str(min_sdk),
                '--target-sdk-version', str(target_sdk),
                '--manifest', '@INPUT0@',
                '--java', '@OUTDIR@/java',
                '-I', '@INPUT1@'
            ] + ['@INPUT2@'] if resources is not None else []),
            [manifest_src, android_platform_jar] + [resources] if resources is not None else [],
            ['container.apk', os.sep.join(['java', *app_id.split('.'), 'R.java'])]
        )
        tgts.append(container_tgt)

        java_sources = [container_res]
        java_jars = []

        for source in sources:
            if isinstance(source, Jar):
                java_jars.append(source)
            else:
                java_sources.append(source)

        app_java_tgt = Jar(
            app_id,
            # using work_dir here is problematic, as it is used by the backend to determine the -sourcepath argument.
            # Specifically, with this being work dir, the backend adds <srcroot>/<subdir>/<app_id>.p/ (which doesn't
            # exist and doesn't add <srcroot>/<subdir> (which should be added).
            work_dir,
            state.subproject,
            MachineChoice.HOST,
            self.interpreter.source_strings_to_files(java_sources),
            None, [],
            state.environment,
            self.interpreter.compilers[MachineChoice.HOST],
            {
                'language_args': {
                    # setting the classpath here sucks, I'd rather extend mesons link_with: jar support to external jars
                    'java': javac_args + ['-cp', ':'.join([android_platform_jar])],
                },
                # TODO: link_depends does not work for java
                'link_depends': javac_tgt_deps
            }
        )
        tgts.append(app_java_tgt)
        java_jars.append(app_java_tgt)

        dexed = CustomTarget(
            'classes.dex',
            work_dir,
            state.subproject,
            state.environment,
            [
                tools.d8,
                '--classpath', ':'.join([android_platform_jar]),
                '--output', '@OUTDIR@',
                '@INPUT@'
            ],
            java_jars,
            ['classes.dex']
        )
        tgts.append(dexed)

        merged = CustomTarget(
            'merged.apk',
            work_dir,
            state.subproject,
            state.environment,
            [
                *state.environment.get_build_command(), '--internal',
                'android', 'zipmerge',
                '@OUTPUT@', '@INPUT@'
            ],
            [container_apk, dexed],
            ['merged.apk']
        )
        tgts.append(merged)

        signing_data: T.Optional[T.Tuple[str, str, str, str, str]] = None
        # TODO: potentially have keystore, alias, keystore_password & key_password kwargs?
        #       It's the way gradle does it, but in our case that would
        #       imply leaking the keystore password in the ninja file.
        android_user_home = os.getenv('ANDROID_USER_HOME') or os.path.expanduser('~/.android/')
        debug_keystore_loc = os.path.join(android_user_home, 'debug.keystore')
        if os.path.isfile(os.path.expanduser(debug_keystore_loc)):
            signing_data = (debug_keystore_loc, 'AndroidDebugKey', 'android', 'android', 'debugsigned')
        else:
            mlog.warning('Unable to find debug keystore, the generated apk will not be signed')

        final_tgt_kwargs: T.Dict[str, T.Any] = {
            'build_by_default': True,
            'install': kwargs['install'],
            'install_dir': kwargs['install_dir'],
            'install_tag': kwargs['install_tag']
        }

        final = aligned = CustomTarget(
            f'{app_id}-unsigned.apk',
            work_dir if signing_data is not None else state.subdir,
            state.subproject,
            state.environment,
            [
                tools.zipalign,
                '-P', '16', '4',
                '@INPUT@',
                '-f', '@OUTPUT@'
            ],
            [merged],
            [f'{app_id}-unsigned.apk'],
            **({} if signing_data is not None else final_tgt_kwargs)
        )
        tgts.append(aligned)

        if signing_data is not None:
            ks, alias, ks_pw, key_pw, suffix = signing_data
            final = signed = CustomTarget(
                f'{app_id}-{suffix}.apk',
                state.subdir,
                state.subproject,
                state.environment,
                [
                    tools.apksigner, 'sign',
                    '--ks', '@INPUT1@',
                    '--ks-key-alias', alias,
                    '--ks-pass', f'pass:{ks_pw}',
                    '--key-pass', f'pass:{key_pw}',
                    '--in', '@INPUT0@',
                    '--out', '@OUTPUT@'
                ],
                [aligned, File.from_absolute_file(debug_keystore_loc)],
                [f'{app_id}-{suffix}.apk'],
                **final_tgt_kwargs
            )
            tgts.append(signed)

        return ModuleReturnValue(final, tgts)

def initialize(interpreter: 'Interpreter') -> AndroidModule:
    return AndroidModule(interpreter)
