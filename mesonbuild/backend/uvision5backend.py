# Copyright 2014-2019 The Meson development team

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import xml.etree.ElementTree as etree

from . import backends
from ..mesonlib import File, MachineChoice, MesonException, EnvironmentException
from .. import compilers
from .. import mlog

XMLNS = 'http://www.w3.org/2001/XMLSchema-instance'
LOC_ATTRIB = '{%s}noNameSpaceSchemaLocation' % XMLNS
XML_ATTRIB = {LOC_ATTRIB: "project_proj.xsd"}

SRC_FILE_TYPE = '1'
ARM_ASSEMBLY_FILE_TYPE = '2'

KEIL_OPTIM_SETTING_O0 = '1'
KEIL_OPTIM_SETTING_O1 = '2'
KEIL_OPTIM_SETTING_O2 = '3'
KEIL_OPTIM_SETTING_O3 = '4'
KEIL_OPTIM_SETTING_OSPACE = '0'
KEIL_OPTIM_SETTING_OTIME = '1'

class UVision5Backend(backends.Backend):

    def __init__(self, build):
        super().__init__(build)
        if not self.environment.is_cross_build():
            raise EnvironmentException('UVision5 Backend supports only cross-compilation.')
        self.name = 'uvision5'
        self.src_dir_list = []
        self.exclude_src_list = []
        self.rom_start_addr = ''
        self.rom_size = ''
        self.ram1_start_addr = ''
        self.ram1_size = ''
        self.ram2_start_addr = ''
        self.ram2_size = ''
        self.scatter_file_path = ''
        self.linker_args = ''
        self.optimize_level = KEIL_OPTIM_SETTING_O2 # default: -O2
        self.optimize_for_time = KEIL_OPTIM_SETTING_OSPACE # default: -Ospace
        self.use_c99 = '1'
        self.use_gnu = '0'
        self.c_args = ''
        self.output_axf_name = ''
        self.src_list = []
        self.header_path_list = []
        self.uvision_filename = ''

    def get_cross_stdlib_args(self, target, compiler):
        return []

    @classmethod
    def get_source_file_type(cls, src):
        ext = src.split('.')[1]
        if ext in ('c'):
            return SRC_FILE_TYPE
        if ext in ('s'):
            return ARM_ASSEMBLY_FILE_TYPE
        raise MesonException('Could not guess file type from source file %s.' % src)

    def select_optimize_options(self, option):
        optim = self.optimize_level
        optim_time = self.optimize_for_time
        if (option == '-O0'):
            optim = KEIL_OPTIM_SETTING_O0
        elif (option == '-O1'):
            optim = KEIL_OPTIM_SETTING_O1
        elif (option == '-O2'):
            optim = KEIL_OPTIM_SETTING_O2
        elif (option == '-O3'):
            optim = KEIL_OPTIM_SETTING_O3
        elif (option.lower() in ('-otime', '-ospace')):
            optim_time = (KEIL_OPTIM_SETTING_OTIME if (option.lower() == '-otime') else
                          KEIL_OPTIM_SETTING_OSPACE)
        return optim, optim_time

    def extract_sct_file_path_from_link_args(self, link_args):
        for i in link_args:
            if (i == "--scatter"):
                scat_file_index = link_args.index(i)
                scat_file_index += 1
                return link_args[scat_file_index]
        return None

    def generate(self, interp):
        self.interpreter = interp
        host_cpu = self.interpreter.builtin['host_machine'].cpu_method(None, None)
        if host_cpu.lower() in ['cortex-m4fp', 'cortex-m0+']:
            self.cpu_type = host_cpu.lower()
        else:
            raise MesonException('Unsupported CPU type for uVision5: ' + host_cpu)
        self.uvision_filename = os.path.join(self.build_dir, self.build.project_name + '.uvprojx')

        # Build the XML
        proj_ele = self.build_xml_node('Project', None, XML_ATTRIB)

        schema_ele = self.build_xml_node('SchemaVersion', '2.1')
        proj_ele.append(schema_ele)

        header_ele = self.build_xml_node('Header',
                                         '### uVision Project, (C) Keil Software')
        proj_ele.append(header_ele)

        tars_ele = self.build_xml_node('Targets')
        tar_ele = self.generate_target()
        if tar_ele is not None:
            tars_ele.append(tar_ele)

        proj_ele.append(tars_ele)

        rte_ele = self.build_rte_ele()
        proj_ele.append(rte_ele)

        # XML ready. Pretty-print to output file
        self.indent_xml(proj_ele)
        tree = etree.ElementTree(proj_ele)
        tree.write(self.uvision_filename, xml_declaration=True, encoding='utf-8', method='xml')

        print("Uvprojx created here: ", self.uvision_filename)

    def generate_target(self):
        """
        Checks for an executable Target (cross-build) in current build,
        with the same name as the current project name, builds the target and returns.
        If no target found, a warning message will be thrown.
        """
        for target in self.build.get_targets().values():
            """
            Currently the uvision5backend can only be used to generate a Keil uvsion5 configuration file
            for an executable target, which:
              - is being cross build (native keyword is false),
              - has same name as the current meson project name and
              - does not have any dependencies on any custom_targets or libraries
            """
            if ((target.get_typename() == 'executable') and target.is_cross and
                    (target.name == self.build.project_name)):

                if any([target.generated, target.objects, target.external_deps, target.link_targets]):
                    raise MesonException('Could not process Executable target - %s, the target has other dependencies.'
                                         % target.name)

                # Populate all global variables with info from target object
                self.output_axf_name = target.filename

                # Source files
                source_list = []
                for i in target.sources:
                    if isinstance(i, File):
                        file_name = i.fname
                        file_path = i.absolute_path(self.source_dir, self.build_dir)
                        file_type = self.get_source_file_type(file_name)
                        source_list.append((file_name, file_path, file_type))
                self.src_list = source_list

                # One compiler for all types of source files
                compiler = target.compilers['c']

                # Compiler arguments
                c_args = ''
                args_list = []
                base_proxy = self.get_base_options_for_target(target)
                # Add compiler args for compiling this target derived from 'base' build
                # options passed on the command-line, in default_options, etc.
                # These have the lowest priority.
                args_list += compilers.get_base_compile_args(base_proxy, compiler)
                # Add compiler args and include paths from several sources; defaults,
                # build options, external dependencies, etc.
                args_list += self.generate_basic_compiler_args(target, compiler, False)
                # Add per-target compile args, f.ex, `c_args : ['-DFOO']`. We set these
                # near the end since these are supposed to override everything else.
                args_list += self.escape_extra_args(compiler,
                                                    target.get_extra_args(compiler.get_language()))

                for i in args_list:
                    if (i[:2] == '-O'):
                        # If optimization options are specified more than once in the project,
                        # then the latest one (the last one) in the list should be in effect.
                        self.optimize_level, self.optimize_for_time = self.select_optimize_options(i)
                    elif (i[:2] == '-D'):
                        c_args += i[2:]
                        c_args += ", "
                self.c_args = c_args[:len(c_args) - 2]

                # Include directories
                #
                # Add include dirs from the `include_directories:` kwarg on the target
                # and from `include_directories:` of internal deps of the target.
                #
                # Target include dirs should override internal deps include dirs.
                # This is handled in BuildTarget.process_kwargs()
                #
                # Include dirs from internal deps should override include dirs from
                # external deps and must maintain the order in which they are specified.
                # Hence, we must reverse the list so that the order is preserved.
                headers = target.get_include_dirs()
                header_list = []
                for i in reversed(headers):
                    basedir = i.get_curdir()
                    # We should iterate include dirs in reversed orders because
                    # -Ipath will add to begin of array. And without reverse
                    # flags will be added in reversed order.
                    for d in reversed(i.get_incdirs()):
                        # Avoid superfluous '/.' at the end of paths when d is '.'
                        if d not in ('', '.'):
                            expdir = os.path.join(basedir, d)
                        else:
                            expdir = basedir
                        srctreedir = os.path.join(self.source_dir, expdir)
                        header_list.append(srctreedir)
                self.header_path_list = header_list
                # Add build directory to the Include dirs list
                self.header_path_list.append(self.build_dir)

                # Linker arguments
                # Add buildtype linker args: optimization level, etc.
                link_args = compiler.get_buildtype_linker_args(
                    self.get_option_for_target('buildtype', target))
                # Add link args added using add_project_link_arguments()
                link_args += self.build.get_project_link_args(
                    compiler, target.subproject, target.is_cross)
                # Add link args added using add_global_link_arguments()
                # These override per-project link arguments
                link_args += self.build.get_global_link_args(compiler, target.is_cross)
                # Link args added from the env: LDFLAGS. We want these to override
                # all the defaults but not the per-target link args.
                link_args += self.environment.coredata.get_external_link_args(
                    MachineChoice.HOST, compiler.get_language())
                link_args += target.link_args
                self.linker_args = ' '.join(link_args)

                # Scatter file path
                self.scatter_file_path = self.extract_sct_file_path_from_link_args(link_args)

                # build the target
                return self.build_target_ele(target.name)
        # No executable target found in the project
        mlog.warning('No executable target has been found. Creating uvision5 project with no targets.')
        return None

    def build_xml_node(self, node_name, text=None, xml_attrib=None):
        """Builds an XML node with the given node_name and text"""
        ele = etree.Element(node_name, attrib=xml_attrib or {})
        if text:
            ele.text = text
        return ele

    def build_ocm_ele(self, node_name, node_type, start_addr, size):
        """Builds an ocm node"""
        ocm_ele = self.build_xml_node(node_name)

        type_ele = self.build_xml_node('Type', node_type)
        ocm_ele.append(type_ele)
        startaddr_ele = self.build_xml_node('StartAddress', start_addr)
        ocm_ele.append(startaddr_ele)
        size_ele = self.build_xml_node('Size', size)
        ocm_ele.append(size_ele)

        return ocm_ele

    def build_ocm_nodes(self):
        """Build OCMs"""

        onchipmem_ele = self.build_xml_node('OnChipMemories')

        ocm1_ele = self.build_ocm_ele('Ocm1', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm1_ele)
        ocm2_ele = self.build_ocm_ele('Ocm2', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm2_ele)
        ocm3_ele = self.build_ocm_ele('Ocm3', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm3_ele)
        ocm4_ele = self.build_ocm_ele('Ocm4', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm4_ele)
        ocm5_ele = self.build_ocm_ele('Ocm5', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm5_ele)
        ocm6_ele = self.build_ocm_ele('Ocm6', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocm6_ele)
        iram_ele = self.build_ocm_ele('IRAM', '0x0', '0x20000000', '0x20000')
        onchipmem_ele.append(iram_ele)
        irom_ele = self.build_ocm_ele('IROM', '0x1', '0x0', '0x40000')
        onchipmem_ele.append(irom_ele)
        xram_ele = self.build_ocm_ele('XRAM', '0x0', '0x0', '0x0')
        onchipmem_ele.append(xram_ele)
        ocr1_ele = self.build_ocm_ele('OCR_RVCT1', '0x1', '0x0', '0x0')
        onchipmem_ele.append(ocr1_ele)
        ocr2_ele = self.build_ocm_ele('OCR_RVCT2', '0x1', '0x0', '0x0')
        onchipmem_ele.append(ocr2_ele)
        ocr3_ele = self.build_ocm_ele('OCR_RVCT3', '0x1', '0x0', '0x0')
        onchipmem_ele.append(ocr3_ele)
        ocr4_ele = self.build_ocm_ele('OCR_RVCT4', '0x1', self.rom_start_addr, self.rom_size)
        onchipmem_ele.append(ocr4_ele)
        ocr5_ele = self.build_ocm_ele('OCR_RVCT5', '0x1', '0x0', '0x0')
        onchipmem_ele.append(ocr5_ele)
        ocr6_ele = self.build_ocm_ele('OCR_RVCT6', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocr6_ele)
        ocr7_ele = self.build_ocm_ele('OCR_RVCT7', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocr7_ele)
        ocr8_ele = self.build_ocm_ele('OCR_RVCT8', '0x0', '0x0', '0x0')
        onchipmem_ele.append(ocr8_ele)
        ocr9_ele = self.build_ocm_ele('OCR_RVCT9', '0x0', self.ram1_start_addr, self.ram1_size)
        onchipmem_ele.append(ocr9_ele)
        ocr10_ele = self.build_ocm_ele('OCR_RVCT10', '0x0', self.ram2_start_addr, self.ram2_size)
        onchipmem_ele.append(ocr10_ele)

        return onchipmem_ele

    def build_armadsmisc_ele(self):
        """Build ArmAdsMisc node"""

        armadsmisc_ele = self.build_xml_node('ArmAdsMisc')

        genlist_ele = self.build_xml_node('GenerateListings', '0')
        armadsmisc_ele.append(genlist_ele)
        ashll_ele = self.build_xml_node('asHll', '1')
        armadsmisc_ele.append(ashll_ele)
        asasm_ele = self.build_xml_node('asAsm', '1')
        armadsmisc_ele.append(asasm_ele)
        asmacx_ele = self.build_xml_node('asMacX', '1')
        armadsmisc_ele.append(asmacx_ele)
        assyms_ele = self.build_xml_node('asSyms', '1')
        armadsmisc_ele.append(assyms_ele)
        asfals_ele = self.build_xml_node('asFals', '1')
        armadsmisc_ele.append(asfals_ele)
        asdbgd_ele = self.build_xml_node('asDbgD', '1')
        armadsmisc_ele.append(asdbgd_ele)
        asform_ele = self.build_xml_node('asForm', '1')
        armadsmisc_ele.append(asform_ele)
        ldlst_ele = self.build_xml_node('ldLst', '0')
        armadsmisc_ele.append(ldlst_ele)
        ldmm_ele = self.build_xml_node('ldmm', '1')
        armadsmisc_ele.append(ldmm_ele)
        ldxref_ele = self.build_xml_node('ldXref', '1')
        armadsmisc_ele.append(ldxref_ele)
        bigend_ele = self.build_xml_node('BigEnd', '0')
        armadsmisc_ele.append(bigend_ele)
        adsalst_ele = self.build_xml_node('AdsALst', '1')
        armadsmisc_ele.append(adsalst_ele)
        adsacrf_ele = self.build_xml_node('AdsACrf', '1')
        armadsmisc_ele.append(adsacrf_ele)
        adsanop_ele = self.build_xml_node('AdsANop', '0')
        armadsmisc_ele.append(adsanop_ele)
        adsanot_ele = self.build_xml_node('AdsANot', '0')
        armadsmisc_ele.append(adsanot_ele)
        adsllst_ele = self.build_xml_node('AdsLLst', '1')
        armadsmisc_ele.append(adsllst_ele)
        adslmap_ele = self.build_xml_node('AdsLmap', '1')
        armadsmisc_ele.append(adslmap_ele)
        adslcgr_ele = self.build_xml_node('AdsLcgr', '1')
        armadsmisc_ele.append(adslcgr_ele)
        adslsym_ele = self.build_xml_node('AdsLsym', '1')
        armadsmisc_ele.append(adslsym_ele)
        adslszi_ele = self.build_xml_node('AdsLszi', '1')
        armadsmisc_ele.append(adslszi_ele)
        adsltoi_ele = self.build_xml_node('AdsLtoi', '1')
        armadsmisc_ele.append(adsltoi_ele)
        adslsun_ele = self.build_xml_node('AdsLsun', '1')
        armadsmisc_ele.append(adslsun_ele)
        adslven_ele = self.build_xml_node('AdsLven', '1')
        armadsmisc_ele.append(adslven_ele)
        adslsxf_ele = self.build_xml_node('AdsLsxf', '1')
        armadsmisc_ele.append(adslsxf_ele)

        rvct_ele = self.build_xml_node('RvctClst', '0')
        armadsmisc_ele.append(rvct_ele)
        genpplst_ele = self.build_xml_node('GenPPlst', '0')
        armadsmisc_ele.append(genpplst_ele)
        if self.cpu_type == 'cortex-m0+':
            adscputype_ele = self.build_xml_node('AdsCpuType', 'Cortex-M0+')
        else:
            adscputype_ele = self.build_xml_node('AdsCpuType', 'Cortex-M4')
        armadsmisc_ele.append(adscputype_ele)
        rvctdevname_ele = self.build_xml_node('RvctDeviceName')
        armadsmisc_ele.append(rvctdevname_ele)

        mos_ele = self.build_xml_node('mOS', '0')
        armadsmisc_ele.append(mos_ele)
        uocrom_ele = self.build_xml_node('uocRom', '0')
        armadsmisc_ele.append(uocrom_ele)
        uocram_ele = self.build_xml_node('uocRam', '0')
        armadsmisc_ele.append(uocram_ele)
        hadirom_ele = self.build_xml_node('hadIROM', '1')
        armadsmisc_ele.append(hadirom_ele)
        hadiram_ele = self.build_xml_node('hadIRAM', '1')
        armadsmisc_ele.append(hadiram_ele)
        hadxram_ele = self.build_xml_node('hadXRAM', '0')
        armadsmisc_ele.append(hadxram_ele)
        uocxram_ele = self.build_xml_node('uocXRam', '0')
        armadsmisc_ele.append(uocxram_ele)

        rvdsvp_ele = self.build_xml_node('RvdsVP', '2')
        armadsmisc_ele.append(rvdsvp_ele)
        hadiram2_ele = self.build_xml_node('hadIRAM2', '0')
        armadsmisc_ele.append(hadiram2_ele)
        hadirom2_ele = self.build_xml_node('hadIROM2', '0')
        armadsmisc_ele.append(hadirom2_ele)
        stupsel_ele = self.build_xml_node('StupSel', '8')
        armadsmisc_ele.append(stupsel_ele)
        useulib_ele = self.build_xml_node('useUlib', '1')
        armadsmisc_ele.append(useulib_ele)
        endsel_ele = self.build_xml_node('EndSel', '1')
        armadsmisc_ele.append(endsel_ele)
        ultcg_ele = self.build_xml_node('uLtcg', '0')
        armadsmisc_ele.append(ultcg_ele)
        nsecure_ele = self.build_xml_node('nSecure', '0')
        armadsmisc_ele.append(nsecure_ele)
        roseld_ele = self.build_xml_node('RoSelD', '3')
        armadsmisc_ele.append(roseld_ele)
        rwseld_ele = self.build_xml_node('RwSelD', '3')
        armadsmisc_ele.append(rwseld_ele)
        codesel_ele = self.build_xml_node('CodeSel', '0')
        armadsmisc_ele.append(codesel_ele)
        optfeed_ele = self.build_xml_node('OptFeed', '0')
        armadsmisc_ele.append(optfeed_ele)
        nozi1_ele = self.build_xml_node('NoZi1', '0')
        armadsmisc_ele.append(nozi1_ele)
        nozi2_ele = self.build_xml_node('NoZi2', '0')
        armadsmisc_ele.append(nozi2_ele)
        nozi3_ele = self.build_xml_node('NoZi3', '0')
        armadsmisc_ele.append(nozi3_ele)
        nozi4_ele = self.build_xml_node('NoZi4', '1')
        armadsmisc_ele.append(nozi4_ele)
        nozi5_ele = self.build_xml_node('NoZi5', '1')
        armadsmisc_ele.append(nozi5_ele)

        ro1chk_ele = self.build_xml_node('Ro1Chk', '0')
        armadsmisc_ele.append(ro1chk_ele)
        ro2chk_ele = self.build_xml_node('Ro2Chk', '0')
        armadsmisc_ele.append(ro2chk_ele)
        ro3chk_ele = self.build_xml_node('Ro3Chk', '0')
        armadsmisc_ele.append(ro3chk_ele)
        ir1chk_ele = self.build_xml_node('Ir1Chk', '1')
        armadsmisc_ele.append(ir1chk_ele)
        ir2chk_ele = self.build_xml_node('Ir2Chk', '0')
        armadsmisc_ele.append(ir2chk_ele)
        ra1chk_ele = self.build_xml_node('Ra1Chk', '0')
        armadsmisc_ele.append(ra1chk_ele)
        ra2chk_ele = self.build_xml_node('Ra2Chk', '0')
        armadsmisc_ele.append(ra2chk_ele)
        ra3chk_ele = self.build_xml_node('Ra3Chk', '0')
        armadsmisc_ele.append(ra3chk_ele)
        im1chk_ele = self.build_xml_node('Im1Chk', '1')
        armadsmisc_ele.append(im1chk_ele)
        im2chk_ele = self.build_xml_node('Im2Chk', '1')
        armadsmisc_ele.append(im2chk_ele)

        ocms_ele = self.build_ocm_nodes()
        armadsmisc_ele.append(ocms_ele)

        rvctstartvec_ele = self.build_xml_node('RvctStartVector')
        armadsmisc_ele.append(rvctstartvec_ele)

        return armadsmisc_ele

    def build_target_stat_ele(self):
        """Build target status element"""
        # Top level node
        tar_stat_ele = self.build_xml_node('TargetStatus')

        # Now populate all children
        error_ele = self.build_xml_node('Error', '0')
        tar_stat_ele.append(error_ele)
        exit_code_stop_ele = self.build_xml_node('ExitCodeStop', '0')
        tar_stat_ele.append(exit_code_stop_ele)
        button_stop_ele = self.build_xml_node('ButtonStop', '0')
        tar_stat_ele.append(button_stop_ele)
        notgen_ele = self.build_xml_node('NotGenerated', '0')
        tar_stat_ele.append(notgen_ele)
        invalid_flash_ele = self.build_xml_node('InvalidFlash', '1')
        tar_stat_ele.append(invalid_flash_ele)

        return tar_stat_ele

    def build_compile_make_ele(self, node_name, stop_node1_name, stop_node2_name):
        """Build Before/After Compile/Make node"""
        top_ele = self.build_xml_node(node_name)

        userprog1_ele = self.build_xml_node('RunUserProg1', '0')
        top_ele.append(userprog1_ele)
        userprog2_ele = self.build_xml_node('RunUserProg2', '0')
        top_ele.append(userprog2_ele)
        userprog1name_ele = self.build_xml_node('UserProg1Name', '0')
        top_ele.append(userprog1name_ele)
        userprog2name_ele = self.build_xml_node('UserProg2Name', '0')
        top_ele.append(userprog2name_ele)
        userprog1dos16mode_ele = self.build_xml_node('UserProg1Dos16Mode', '0')
        top_ele.append(userprog1dos16mode_ele)
        userprog2dos16mode_ele = self.build_xml_node('UserProg2Dos16Mode', '0')
        top_ele.append(userprog2dos16mode_ele)
        stop1_ele = self.build_xml_node(stop_node1_name, '0')
        top_ele.append(stop1_ele)
        stop2_ele = self.build_xml_node(stop_node2_name, '0')
        top_ele.append(stop2_ele)

        return top_ele

    def build_target_common_opt_ele(self):
        """Build Target Common Option Element"""
        # Top level node
        tarcomopt_ele = self.build_xml_node('TargetCommonOption')

        # Now populate all children
        if self.cpu_type == 'cortex-m0+':
            dev_ele = self.build_xml_node('Device', 'ARMCM0P')
        else:
            dev_ele = self.build_xml_node('Device', 'ARMCM4_FP')
        tarcomopt_ele.append(dev_ele)
        vend_ele = self.build_xml_node('Vendor', 'ARM')
        tarcomopt_ele.append(vend_ele)
        packid_ele = self.build_xml_node('PackID', 'ARM.CMSIS.5.3.0')
        tarcomopt_ele.append(packid_ele)
        packurl_ele = self.build_xml_node('PackURL', 'http://www.keil.com/pack/')
        tarcomopt_ele.append(packurl_ele)
        if self.cpu_type == 'cortex-m0+':
            cpu_ele = self.build_xml_node('Cpu', 'IRAM(0x20000000,0x00020000) IROM(0x00000000,0x00040000) CPUTYPE("Cortex-M0+") CLOCK(12000000) ESEL ELITTLE')
        else:
            cpu_ele = self.build_xml_node('Cpu', 'IRAM(0x20000000,0x00020000) IROM(0x00000000,0x00040000) CPUTYPE("Cortex-M4") FPU2 CLOCK(12000000) ESEL ELITTLE')
        tarcomopt_ele.append(cpu_ele)
        flash_util_spec_ele = self.build_xml_node('FlashUtilSpec')
        tarcomopt_ele.append(flash_util_spec_ele)
        startup_file_ele = self.build_xml_node('StartupFile')
        tarcomopt_ele.append(startup_file_ele)
        flash_drvr_dll_ele = self.build_xml_node('FlashDriverDll', 'UL2CM3(-S0 -C0 -P0 -FD20000000 -FC1000)')
        tarcomopt_ele.append(flash_drvr_dll_ele)
        devid_ele = self.build_xml_node('DeviceId', '0')
        tarcomopt_ele.append(devid_ele)
        if self.cpu_type == 'cortex-m0+':
            regfile_ele = self.build_xml_node('RegisterFile', '$$Device:ARMCM0P$Device\\ARM\\ARMCM0plus\\Include\\ARMCM0plus.h')
        else:
            regfile_ele = self.build_xml_node('RegisterFile', '$$Device:ARMCM4_FP$Device\\ARM\\ARMCM4\\Include\\ARMCM4_FP.h')
        tarcomopt_ele.append(regfile_ele)
        memenv_ele = self.build_xml_node('MemoryEnv')
        tarcomopt_ele.append(memenv_ele)
        cmp_ele = self.build_xml_node('Cmp')
        tarcomopt_ele.append(cmp_ele)
        asm_ele = self.build_xml_node('Asm')
        tarcomopt_ele.append(asm_ele)
        linker_ele = self.build_xml_node('Linker')
        tarcomopt_ele.append(linker_ele)
        ohstring_ele = self.build_xml_node('OHString')
        tarcomopt_ele.append(ohstring_ele)
        infi_ele = self.build_xml_node('InfinionOptionDll')
        tarcomopt_ele.append(infi_ele)
        sle66cmisc_ele = self.build_xml_node('SLE66CMisc')
        tarcomopt_ele.append(sle66cmisc_ele)
        sle66amisc_ele = self.build_xml_node('SLE66AMisc')
        tarcomopt_ele.append(sle66amisc_ele)
        sle66linkermisc_ele = self.build_xml_node('SLE66LinkerMisc')
        tarcomopt_ele.append(sle66linkermisc_ele)
        sfdfile_ele = self.build_xml_node('SFDFile')
        tarcomopt_ele.append(sfdfile_ele)
        bcustsvd_ele = self.build_xml_node('bCustSvd', '0')
        tarcomopt_ele.append(bcustsvd_ele)
        useenv_ele = self.build_xml_node('UseEnv', '0')
        tarcomopt_ele.append(useenv_ele)
        binpath_ele = self.build_xml_node('BinPath')
        tarcomopt_ele.append(binpath_ele)
        incpath_ele = self.build_xml_node('IncludePath')
        tarcomopt_ele.append(incpath_ele)
        libpath_ele = self.build_xml_node('LibPath')
        tarcomopt_ele.append(libpath_ele)
        regfilepath_ele = self.build_xml_node('RegisterFilePath')
        tarcomopt_ele.append(regfilepath_ele)
        dbregfilepath_ele = self.build_xml_node('DBRegisterFilePath')
        tarcomopt_ele.append(dbregfilepath_ele)

        tarcomopt_ele.append(self.build_target_stat_ele())

        outdir_ele = self.build_xml_node('OutputDirectory', '.\\Objects\\')
        tarcomopt_ele.append(outdir_ele)
        outname_ele = self.build_xml_node('OutputName', self.output_axf_name)
        tarcomopt_ele.append(outname_ele)
        create_exe_ele = self.build_xml_node('CreateExecutable', '1')
        tarcomopt_ele.append(create_exe_ele)
        create_lib_ele = self.build_xml_node('CreateLib', '0')
        tarcomopt_ele.append(create_lib_ele)
        create_hexfile_ele = self.build_xml_node('CreateHexFile', '0')
        tarcomopt_ele.append(create_hexfile_ele)
        debuginfo_ele = self.build_xml_node('DebugInformation', '1')
        tarcomopt_ele.append(debuginfo_ele)
        browseinfo_ele = self.build_xml_node('BrowseInformation', '1')
        tarcomopt_ele.append(browseinfo_ele)
        listing_path_ele = self.build_xml_node('ListingPath', '.\\Listings\\')
        tarcomopt_ele.append(listing_path_ele)
        hexformatsel_ele = self.build_xml_node('HexFormatSelection', '1')
        tarcomopt_ele.append(hexformatsel_ele)
        merge32k_ele = self.build_xml_node('Merge32K', '0')
        tarcomopt_ele.append(merge32k_ele)
        create_bat_file_ele = self.build_xml_node('CreateBatchFile', '0')
        tarcomopt_ele.append(create_bat_file_ele)

        before_compile_ele = self.build_compile_make_ele('BeforeCompile', 'nStopU1X', 'nStopU2X')
        tarcomopt_ele.append(before_compile_ele)
        before_make_ele = self.build_compile_make_ele('BeforeMake', 'nStopB1X', 'nStopB2X')
        tarcomopt_ele.append(before_make_ele)
        after_make_ele = self.build_compile_make_ele('AfterMake', 'nStopA1X', 'nStopA2X')
        tarcomopt_ele.append(after_make_ele)

        selected4batbuild_ele = self.build_xml_node('SelectedForBatchBuild', '0')
        tarcomopt_ele.append(selected4batbuild_ele)
        svcsidstr_ele = self.build_xml_node('SVCSIdString')
        tarcomopt_ele.append(svcsidstr_ele)

        return tarcomopt_ele

    def build_common_prop_ele(self):
        """Build the common property element"""
        # top-level node
        commonprop_ele = self.build_xml_node('CommonProperty')

        # Now populate the children
        usecppcomp_ele = self.build_xml_node('UseCPPCompiler', '0')
        commonprop_ele.append(usecppcomp_ele)
        rvctcodeconst_ele = self.build_xml_node('RVCTCodeConst', '0')
        commonprop_ele.append(rvctcodeconst_ele)
        rvctzi_ele = self.build_xml_node('RVCTZI', '0')
        commonprop_ele.append(rvctzi_ele)
        rvctotherdata_ele = self.build_xml_node('RVCTOtherData', '0')
        commonprop_ele.append(rvctotherdata_ele)
        modulesel_ele = self.build_xml_node('ModuleSelection', '0')
        commonprop_ele.append(modulesel_ele)
        incinbuild_ele = self.build_xml_node('IncludeInBuild', '1')
        commonprop_ele.append(incinbuild_ele)
        alwaysbuild_ele = self.build_xml_node('AlwaysBuild', '0')
        commonprop_ele.append(alwaysbuild_ele)
        genassemblyfile_ele = self.build_xml_node('GenerateAssemblyFile', '0')
        commonprop_ele.append(genassemblyfile_ele)
        assembleassemblyfile_ele = self.build_xml_node('AssembleAssemblyFile', '0')
        commonprop_ele.append(assembleassemblyfile_ele)
        publicsonly_ele = self.build_xml_node('PublicsOnly', '0')
        commonprop_ele.append(publicsonly_ele)
        stoponexitcode_ele = self.build_xml_node('StopOnExitCode', '3')
        commonprop_ele.append(stoponexitcode_ele)
        customarg_ele = self.build_xml_node('CustomArgument')
        commonprop_ele.append(customarg_ele)
        inclibmod_ele = self.build_xml_node('IncludeLibraryModules')
        commonprop_ele.append(inclibmod_ele)
        comprimg_ele = self.build_xml_node('ComprImg', '1')
        commonprop_ele.append(comprimg_ele)

        return commonprop_ele

    def build_dll_opt_ele(self):
        """Build DLL option element"""
        dll_opt_ele = self.build_xml_node('DllOption')

        simdllname_ele = self.build_xml_node('SimDllName', 'SARMCM3.DLL')
        dll_opt_ele.append(simdllname_ele)
        simdllargs_ele = self.build_xml_node('SimDllArguments', '  -MPU')
        dll_opt_ele.append(simdllargs_ele)
        simdlgdll_ele = self.build_xml_node('SimDlgDll', 'DCM.DLL')
        dll_opt_ele.append(simdlgdll_ele)
        simdlgdllargs_ele = self.build_xml_node('SimDlgDllArguments', '-pCM4')
        dll_opt_ele.append(simdlgdllargs_ele)
        tardllname_ele = self.build_xml_node('TargetDllName', 'SARMCM3.DLL')
        dll_opt_ele.append(tardllname_ele)
        tardllargs_ele = self.build_xml_node('TargetDllArguments', ' -MPU')
        dll_opt_ele.append(tardllargs_ele)
        tardlgdll_ele = self.build_xml_node('TargetDlgDll', 'TCM.DLL')
        dll_opt_ele.append(tardlgdll_ele)
        tardlgdllargs_ele = self.build_xml_node('TargetDlgDllArguments', '-pCM4')
        dll_opt_ele.append(tardlgdllargs_ele)

        return dll_opt_ele

    def build_debug_opt_ele(self):
        """Build DebugOption element"""
        debug_opt_ele = self.build_xml_node('DebugOption')
        opthx_ele = self.build_xml_node('OPTHX')

        hexsel_ele = self.build_xml_node('HexSelection', '1')
        opthx_ele.append(hexsel_ele)
        hexrangelowaddr_ele = self.build_xml_node('HexRangeLowAddress', '0')
        opthx_ele.append(hexrangelowaddr_ele)
        hexrangehighaddr_ele = self.build_xml_node('HexRangeHighAddress', '0')
        opthx_ele.append(hexrangehighaddr_ele)
        hexoff_ele = self.build_xml_node('HexOffset', '0')
        opthx_ele.append(hexoff_ele)
        oh166reclen_ele = self.build_xml_node('Oh166RecLen', '16')
        opthx_ele.append(oh166reclen_ele)

        debug_opt_ele.append(opthx_ele)

        return debug_opt_ele

    def build_utils_ele(self):
        """Build Utilities element"""
        utils_ele = self.build_xml_node('Utilities')

        flash1_ele = self.build_xml_node('Flash1')

        usetargdll_ele = self.build_xml_node('UseTargetDll', '1')
        flash1_ele.append(usetargdll_ele)
        useexttool_ele = self.build_xml_node('UseExternalTool', '0')
        flash1_ele.append(useexttool_ele)
        runind_ele = self.build_xml_node('RunIndependent', '0')
        flash1_ele.append(runind_ele)
        updflashb4debug_ele = self.build_xml_node('UpdateFlashBeforeDebugging', '1')
        flash1_ele.append(updflashb4debug_ele)
        cap_ele = self.build_xml_node('Capability', '0')
        flash1_ele.append(cap_ele)
        drvrsel_ele = self.build_xml_node('DriverSelection', '-1')
        flash1_ele.append(drvrsel_ele)

        utils_ele.append(flash1_ele)

        busetdr_ele = self.build_xml_node('bUseTDR')
        utils_ele.append(busetdr_ele)
        flash2_ele = self.build_xml_node('Flash2', 'BIN\\UL2CM3.DLL')
        utils_ele.append(flash2_ele)
        flash3_ele = self.build_xml_node('Flash3')
        utils_ele.append(flash3_ele)
        flash4_ele = self.build_xml_node('Flash4')
        utils_ele.append(flash4_ele)
        pfcarmout_ele = self.build_xml_node('pFcarmOut')
        utils_ele.append(pfcarmout_ele)
        pfcarmgrp_ele = self.build_xml_node('pFcarmGrp')
        utils_ele.append(pfcarmgrp_ele)
        pfcarmroot_ele = self.build_xml_node('pFcArmRoot')
        utils_ele.append(pfcarmroot_ele)
        fcarmlst_ele = self.build_xml_node('FcArmLst')
        utils_ele.append(fcarmlst_ele)

        return utils_ele

    def build_cads_ele(self):
        """Build Cads element"""
        cads_ele = self.build_xml_node('Cads')

        interw_ele = self.build_xml_node('interw', '1')
        cads_ele.append(interw_ele)
        optim_ele = self.build_xml_node('Optim', self.optimize_level)
        cads_ele.append(optim_ele)
        otime_ele = self.build_xml_node('oTime', self.optimize_for_time)
        cads_ele.append(otime_ele)
        splitls_ele = self.build_xml_node('SplitLS', '0')
        cads_ele.append(splitls_ele)
        oneelfs_ele = self.build_xml_node('OneElfS', '0')
        cads_ele.append(oneelfs_ele)
        strict_ele = self.build_xml_node('Strict', '0')
        cads_ele.append(strict_ele)
        enumint_ele = self.build_xml_node('EnumInt', '0')
        cads_ele.append(enumint_ele)
        plainch_ele = self.build_xml_node('PlainCh', '0')
        cads_ele.append(plainch_ele)
        ropi_ele = self.build_xml_node('Ropi', '0')
        cads_ele.append(ropi_ele)
        rwpi_ele = self.build_xml_node('Rwpi', '0')
        cads_ele.append(rwpi_ele)
        wlevel_ele = self.build_xml_node('wLevel', '2')
        cads_ele.append(wlevel_ele)
        uthumb_ele = self.build_xml_node('uThumb', '0')
        cads_ele.append(uthumb_ele)
        usurpinc_ele = self.build_xml_node('uSurpInc', '1')
        cads_ele.append(usurpinc_ele)
        uc99_ele = self.build_xml_node('uC99', self.use_c99)
        cads_ele.append(uc99_ele)
        ugnu_ele = self.build_xml_node('uGnu', self.use_gnu)
        cads_ele.append(ugnu_ele)
        usexo_ele = self.build_xml_node('useXO', '0')
        cads_ele.append(usexo_ele)
        v6lang_ele = self.build_xml_node('v6Lang', '1')
        cads_ele.append(v6lang_ele)
        v6langp_ele = self.build_xml_node('v6LangP', '1')
        cads_ele.append(v6langp_ele)
        vshorten_ele = self.build_xml_node('vShortEn', '1')
        cads_ele.append(vshorten_ele)
        vshortwch_ele = self.build_xml_node('vShortWch', '1')
        cads_ele.append(vshortwch_ele)
        v6lto_ele = self.build_xml_node('v6Lto', '0')
        cads_ele.append(v6lto_ele)
        v6wte_ele = self.build_xml_node('v6WtE', '0')
        cads_ele.append(v6wte_ele)
        v6rtti_ele = self.build_xml_node('v6Rtti', '0')
        cads_ele.append(v6rtti_ele)

        varcntls_ele = self.build_xml_node('VariousControls')
        misccntls_ele = self.build_xml_node('MiscControls')
        varcntls_ele.append(misccntls_ele)
        define_ele = self.build_xml_node('Define', self.c_args)
        varcntls_ele.append(define_ele)
        undefine_ele = self.build_xml_node('Undefine')
        varcntls_ele.append(undefine_ele)

        incpath_str = ''
        for i in self.header_path_list:
            incpath_str += str(i) + ';'
        incpath_ele = self.build_xml_node('IncludePath', incpath_str[:len(incpath_str) - 1])
        varcntls_ele.append(incpath_ele)

        cads_ele.append(varcntls_ele)

        return cads_ele

    def build_aads_ele(self):
        """Build Aads element"""
        aads_ele = self.build_xml_node('Aads')

        interw_ele = self.build_xml_node('interw', '1')
        aads_ele.append(interw_ele)
        ropi_ele = self.build_xml_node('Ropi', '0')
        aads_ele.append(ropi_ele)
        rwpi_ele = self.build_xml_node('Rwpi', '0')
        aads_ele.append(rwpi_ele)
        thumb_ele = self.build_xml_node('thumb', '0')
        aads_ele.append(thumb_ele)
        splitls_ele = self.build_xml_node('SplitLS', '0')
        aads_ele.append(splitls_ele)
        swstkchk_ele = self.build_xml_node('SwStkChk', '0')
        aads_ele.append(swstkchk_ele)
        nowarn_ele = self.build_xml_node('NoWarn', '0')
        aads_ele.append(nowarn_ele)
        usurpinc_ele = self.build_xml_node('uSurpInc', '1')
        aads_ele.append(usurpinc_ele)
        usexo_ele = self.build_xml_node('useXO', '0')
        aads_ele.append(usexo_ele)
        uclangas_ele = self.build_xml_node('uClangAs', '0')
        aads_ele.append(uclangas_ele)

        varcntls_ele = self.build_xml_node('VariousControls')
        misccntls_ele = self.build_xml_node('MiscControls')
        varcntls_ele.append(misccntls_ele)
        define_ele = self.build_xml_node('Define')
        varcntls_ele.append(define_ele)
        undefine_ele = self.build_xml_node('Undefine')
        varcntls_ele.append(undefine_ele)
        incpath_ele = self.build_xml_node('IncludePath')
        varcntls_ele.append(incpath_ele)

        aads_ele.append(varcntls_ele)

        return aads_ele

    def build_ldads_ele(self):
        """Build LDads element"""
        ldads_ele = self.build_xml_node('LDads')

        umftarg_ele = self.build_xml_node('umfTarg', '0')
        ldads_ele.append(umftarg_ele)
        ropi_ele = self.build_xml_node('Ropi', '0')
        ldads_ele.append(ropi_ele)
        rwpi_ele = self.build_xml_node('Rwpi', '0')
        ldads_ele.append(rwpi_ele)
        nostlib_ele = self.build_xml_node('noStLib', '0')
        ldads_ele.append(nostlib_ele)
        repfail_ele = self.build_xml_node('RepFail', '1')
        ldads_ele.append(repfail_ele)
        usefile_ele = self.build_xml_node('useFile', '0')
        ldads_ele.append(usefile_ele)
        textaddrrange_ele = self.build_xml_node('TextAddressRange', self.rom_start_addr)
        ldads_ele.append(textaddrrange_ele)
        dataaddrrange_ele = self.build_xml_node('DataAddressRange', self.ram1_start_addr)
        ldads_ele.append(dataaddrrange_ele)
        pxobase_ele = self.build_xml_node('pXoBase')
        ldads_ele.append(pxobase_ele)
        scatfile_ele = self.build_xml_node('ScatterFile', self.scatter_file_path)
        ldads_ele.append(scatfile_ele)
        inclibs_ele = self.build_xml_node('IncludeLibs')
        ldads_ele.append(inclibs_ele)
        inclibspath_ele = self.build_xml_node('IncludeLibsPath')
        ldads_ele.append(inclibspath_ele)
        misc_ele = self.build_xml_node('Misc', self.linker_args)
        ldads_ele.append(misc_ele)
        linkinpfile_ele = self.build_xml_node('LinkerInputFile')
        ldads_ele.append(linkinpfile_ele)
        diswarn_ele = self.build_xml_node('DisabledWarnings')
        ldads_ele.append(diswarn_ele)

        return ldads_ele

    def build_src_grp_ele(self):
        """Builds Source Group element"""
        groups_ele = self.build_xml_node('Groups')
        group_ele = self.build_xml_node('Group')

        # Source group with existing or predefined source files list
        groupname_ele = self.build_xml_node('GroupName', 'Source Group 1')
        files_ele = self.build_xml_node('Files')
        for i in self.src_list:
            file_ele = self.build_file_ele(i[0], i[1], i[2])
            files_ele.append(file_ele)
        group_ele.append(groupname_ele)
        group_ele.append(files_ele)

        groups_ele.append(group_ele)
        return groups_ele

    def build_file_ele(self, file_name, path, file_type):
        """Build File element"""
        file_ele = self.build_xml_node('File')
        filename_ele = self.build_xml_node('FileName', file_name)
        filetype_ele = self.build_xml_node('FileType', file_type)
        filepath_ele = self.build_xml_node('FilePath', path)
        file_ele.append(filename_ele)
        file_ele.append(filetype_ele)
        file_ele.append(filepath_ele)
        return file_ele

    def build_target_opt_ele(self):
        """Build TargetOption"""

        tar_opt_ele = self.build_xml_node('TargetOption')

        tar_common_opt_ele = self.build_target_common_opt_ele()
        tar_opt_ele.append(tar_common_opt_ele)
        common_prop_ele = self.build_common_prop_ele()
        tar_opt_ele.append(common_prop_ele)
        dll_opt_ele = self.build_dll_opt_ele()
        tar_opt_ele.append(dll_opt_ele)
        debug_opt_ele = self.build_debug_opt_ele()
        tar_opt_ele.append(debug_opt_ele)
        utils_ele = self.build_utils_ele()
        tar_opt_ele.append(utils_ele)

        tar_armads_ele = self.build_xml_node('TargetArmAds')
        armadsmisc_ele = self.build_armadsmisc_ele()
        tar_armads_ele.append(armadsmisc_ele)
        cads_ele = self.build_cads_ele()
        tar_armads_ele.append(cads_ele)
        aads_ele = self.build_aads_ele()
        tar_armads_ele.append(aads_ele)
        ldads_ele = self.build_ldads_ele()
        tar_armads_ele.append(ldads_ele)
        tar_opt_ele.append(tar_armads_ele)

        return tar_opt_ele

    def build_target_ele(self, target_name):
        """Build Target"""

        tar_ele = self.build_xml_node('Target')

        tarname_ele = self.build_xml_node('TargetName', target_name)
        tar_ele.append(tarname_ele)
        toolsetnum_ele = self.build_xml_node('ToolsetNumber', '0x4')
        tar_ele.append(toolsetnum_ele)
        toolsetname_ele = self.build_xml_node('ToolsetName', 'ARM-ADS')
        tar_ele.append(toolsetname_ele)
        pccused_ele = self.build_xml_node('pCCUsed', '5060750::V5.06 update 6 (build 750)::ARMCC')
        tar_ele.append(pccused_ele)
        uac6_ele = self.build_xml_node('uAC6', '0')
        tar_ele.append(uac6_ele)

        tar_opt_ele = self.build_target_opt_ele()
        tar_ele.append(tar_opt_ele)

        src_grp_ele = self.build_src_grp_ele()
        tar_ele.append(src_grp_ele)

        return tar_ele

    def build_rte_ele(self):
        """Build RTE"""

        rte_ele = self.build_xml_node('RTE')

        apis_ele = self.build_xml_node('apis')
        rte_ele.append(apis_ele)
        comp_ele = self.build_xml_node('components')
        rte_ele.append(comp_ele)
        files_ele = self.build_xml_node('files')
        rte_ele.append(files_ele)

        return rte_ele

    def indent_xml(self, elem, level = 0):
        """Indents the XML as a prerequisite for pretty-printing"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
