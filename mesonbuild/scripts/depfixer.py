# SPDX-License-Identifier: Apache-2.0
# Copyright 2013-2016 The Meson development team

from __future__ import annotations


import sys
import os
import stat
import struct
import shutil
import subprocess
import typing as T

from ..mesonlib import OrderedSet, generate_list, Popen_safe

SHT_STRTAB = 3
DT_NEEDED = 1
DT_RPATH = 15
DT_RUNPATH = 29
DT_STRTAB = 5
DT_SONAME = 14
DT_MIPS_RLD_MAP_REL = 1879048245

# Global cache for tools
INSTALL_NAME_TOOL = False

# -------------------AIX-------------------------
# Reference documents:
# https://www.ibm.com/docs/en/aix/7.1?topic=formats-xcoff-object-file-format
# https://www.ibm.com/docs/en/aix/7.2?topic=formats-ar-file-format-big

# Size of magic number
XCOFF_MAGIC_SIZE = 2


def align(value: int, align_bytes: int) -> int:
    # Function used by AIX to align value to align_bytes
    align_bytes = 1 << align_bytes
    return ((value + align_bytes - 1) // align_bytes) * align_bytes


class XcoffFixedLengthHeader:
    # AIX archive fixed length header (struct fl_hdr)
    FL_HDR_SIZE = 128
    FL_HDR_FORMAT = '8s 20s 20s 20s 20s 20s 20s'

    def __init__(self, file: T.BinaryIO) -> None:
        header_data = file.read(self.FL_HDR_SIZE)
        fl_magic, fl_memoff, fl_gstoff, fl_gst64off, fl_fstmoff, fl_lstmoff, fl_freeoff = struct.unpack(
            self.FL_HDR_FORMAT, header_data
        )
        self.fl_magic = fl_magic
        self.fl_fstmoff = int(fl_fstmoff)


class XcoffArchiveHeader:
    # AIX archive header (struct ar_hdr)
    AR_HDR_SIZE = 114
    AR_HDR_FORMAT = '20s 20s 20s 12s 12s 12s 12s 4s 2s'

    def __init__(self, file: T.BinaryIO) -> None:
        header_data = file.read(self.AR_HDR_SIZE)
        ar_size, ar_nxtmem, ar_prvmem, ar_date, ar_uid, ar_gid, ar_mode, ar_namlen, _ar_name = struct.unpack(
            self.AR_HDR_FORMAT, header_data
        )
        ar_namlen_int = int(ar_namlen.strip())
        # The Magic number always starts at the even byte boundary
        self.ar_namlen = ar_namlen_int if ar_namlen_int % 2 == 0 else ar_namlen_int + 1
        # Seek past the archive member name
        file.seek(self.ar_namlen, os.SEEK_CUR)


class XcoffCompositeFileHeader:
    # XCOFF composite file header
    CFH_HDR_SIZE = 24
    CFH_HDR_SIZE_32 = 20
    CFH_HDR_FORMAT = '2s 2s 4s 8s 2s 2s 4s'
    CFH_HDR_FORMAT_32 = '2s 2s 4s 4s 4s 2s 2s'

    def __init__(self, file: T.BinaryIO, magic: int) -> None:
        if magic == 0x01DF:
            cfh_header_data = file.read(self.CFH_HDR_SIZE_32)
            f_magic, f_nscns, f_timdat, f_symptr, f_nsyms, f_opthdr, f_flags = struct.unpack(
                self.CFH_HDR_FORMAT_32, cfh_header_data
            )
        else:
            cfh_header_data = file.read(self.CFH_HDR_SIZE)
            f_magic, f_nscns, f_timdat, f_symptr, f_opthdr, f_flags, f_nsyms = struct.unpack(
                self.CFH_HDR_FORMAT, cfh_header_data
            )
        self.f_flags = int.from_bytes(f_flags, byteorder='big')
        self.f_opthdr = int.from_bytes(f_opthdr, byteorder='big')


class XcoffAuxiliaryHeader:
    # XCOFF auxiliary header
    AUX_HDR_SIZE = 120
    AUX_HDR_SIZE_32 = 72
    AUX_HDR_FORMAT = '2s 2s 4s 8s 8s 8s 2s 2s 2s 2s 2s 2s 2s 2s 2s 1s 1s 1s 1s 1s 1s 8s 8s 8s 8s 8s 8s 2s 2s 2s 10s'
    AUX_HDR_FORMAT_32 = '2s 2s 4s 4s 4s 4s 4s 4s 4s 2s 2s 2s 2s 2s 2s 2s 2s 2s 1s 1s 4s 4s 4s 1s 1s 1s 1s 2s 2s'

    def __init__(self, file: T.BinaryIO, magic: int, opthdr_size: int) -> None:
        if magic == 0x01DF:
            if opthdr_size < self.AUX_HDR_SIZE_32:
                sys.exit(f'Error: Auxiliary header size {opthdr_size} is too small for 32-bit XCOFF')
            aux_header_data = file.read(self.AUX_HDR_SIZE_32)
            if len(aux_header_data) < self.AUX_HDR_SIZE_32:
                sys.exit(f'Error: Could not read auxiliary header, got {len(aux_header_data)} bytes, expected {self.AUX_HDR_SIZE_32}')
            (o_mflags, o_vstamp, o_tsize, o_dsize, o_bsize, o_entry, o_text_start, o_data_start, o_toc,
             o_snentry, o_sntext, o_sndata, o_sntoc, o_snloader, o_snbss, o_algntext, o_algndata, o_modtype,
             o_cpuflag, o_cputype, o_maxstack, o_maxdata, o_debugger, o_textpsize, o_datapsize, o_stackpsize,
             o_flags, o_sntdata, o_sntbss) = struct.unpack(self.AUX_HDR_FORMAT_32, aux_header_data)
        else:
            if opthdr_size < self.AUX_HDR_SIZE:
                sys.exit(f'Error: Auxiliary header size {opthdr_size} is too small for 64-bit XCOFF')
            aux_header_data = file.read(self.AUX_HDR_SIZE)
            if len(aux_header_data) < self.AUX_HDR_SIZE:
                sys.exit(f'Error: Could not read auxiliary header, got {len(aux_header_data)} bytes, expected {self.AUX_HDR_SIZE}')
            (o_mflags, o_vstamp, o_debugger, o_text_start, o_data_start, o_toc, o_snentry, o_sntext, o_sndata,
             o_sntoc, o_snloader, o_snbss, o_algntext, o_algndata, o_modtype, o_cpuflag, o_cputype, o_textpsize,
             o_datapsize, o_stackpsize, o_flags, o_tsize, o_dsize, o_bsize, o_entry, o_maxstack, o_maxdata,
             o_sntdata, o_sntbss, o_x64flags, dummy) = struct.unpack(self.AUX_HDR_FORMAT, aux_header_data)

        self.o_algntext = int.from_bytes(o_algntext, byteorder='big')
        self.o_algndata = int.from_bytes(o_algndata, byteorder='big')
        self.o_snloader = int.from_bytes(o_snloader, byteorder='big')


class XcoffSectionHeader:
    # XCOFF section header
    SCN_HDR_SIZE = 72
    SCN_HDR_SIZE_32 = 40
    SCN_HDR_FORMAT = '8s 8s 8s 8s 8s 8s 8s 4s 4s 4s 4s'
    SCN_HDR_FORMAT_32 = '8s 4s 4s 4s 4s 4s 4s 2s 2s 2s 2s'

    def __init__(self, file: T.BinaryIO, magic: int) -> None:
        if magic == 0x01DF:
            scn_header_data = file.read(self.SCN_HDR_SIZE_32)
            if len(scn_header_data) < self.SCN_HDR_SIZE_32:
                raise EOFError('End of archive member reached')
            (s_name, s_paddr, s_vaddr, s_size, s_scnptr, s_relptr, s_lnnoptr, s_nreloc, s_nlnno, s_flags,
             dummy) = struct.unpack(self.SCN_HDR_FORMAT_32, scn_header_data)
        else:
            scn_header_data = file.read(self.SCN_HDR_SIZE)
            if len(scn_header_data) < self.SCN_HDR_SIZE:
                raise EOFError('End of archive member reached')
            (s_name, s_paddr, s_vaddr, s_size, s_scnptr, s_relptr, s_lnnoptr, s_nreloc, s_nlnno, s_flags,
             dummy) = struct.unpack(self.SCN_HDR_FORMAT, scn_header_data)
        self.s_scnptr = int.from_bytes(s_scnptr, byteorder='big')


class XcoffLoaderHeader:
    # XCOFF loader header
    LDR_HDR_SIZE = 56
    LDR_HDR_SIZE_32 = 32
    LDR_HDR_FORMAT = '4s 4s 4s 4s 4s 4s 8s 8s 8s 8s'
    LDR_HDR_FORMAT_32 = '4s 4s 4s 4s 4s 4s 4s 4s'

    def __init__(self, file: T.BinaryIO, magic: int) -> None:
        if magic == 0x01DF:
            ldr_header_data = file.read(self.LDR_HDR_SIZE_32)
            (l_version, l_nsyms, l_nreloc, l_istlen, l_nimpid, l_impoff, l_stlen,
             l_stoff) = struct.unpack(self.LDR_HDR_FORMAT_32, ldr_header_data)
        else:
            ldr_header_data = file.read(self.LDR_HDR_SIZE)
            (l_version, l_nsyms, l_nreloc, l_istlen, l_nimpid, l_stlen, l_impoff, l_stoff, l_symoff,
             l_rldoff) = struct.unpack(self.LDR_HDR_FORMAT, ldr_header_data)
        self.l_impoff = int.from_bytes(l_impoff, byteorder='big')
        self.l_istlen = int.from_bytes(l_istlen, byteorder='big')


def traverse_xcoff(file: T.BinaryIO, rpath_dirs_to_remove: T.Set[bytes], new_rpath: T.Optional[bytes], verbose: bool = True) -> None:
    """Traverse XCOFF file or archive and modify Libpath entries.

    Handles both standalone XCOFF shared objects (.so) and XCOFF archives (.a).
    Archives are detected by magic number and processed member by member.
    """
    def dummy_print(*args: object) -> None:
        pass
    log_msg: T.Callable[..., None]
    log_msg = print if verbose else dummy_print

    # Detect if this is an archive by checking for magic number
    magic_check = file.read(8)
    file.seek(0)

    # Read archive headers if this is an archive
    ar_header: T.Optional[XcoffArchiveHeader] = None
    if magic_check == b'<bigaf>\n':
        fl_header = XcoffFixedLengthHeader(file)
        file.seek(fl_header.fl_fstmoff)
        ar_header = XcoffArchiveHeader(file)

    composite_header_pos = file.tell()
    # Read XCOFF magic number
    magic_data = file.read(XCOFF_MAGIC_SIZE)
    if len(magic_data) != XCOFF_MAGIC_SIZE:
        sys.exit(0)
    magic_number = struct.unpack('>H', magic_data)[0]  # Big-endian 16-bit integer
    if magic_number == 0x01DF:
        log_msg(' Changing Libpath for a 32-bit Shared Object')
    elif magic_number == 0x01F7:
        log_msg(' Changing Libpath for a 64-bit Shared Object')
    else:
        log_msg(' Not a shared object')
        sys.exit(0)
    # Reposition to start of XCOFF headers
    file.seek(composite_header_pos)
    cfh_header = XcoffCompositeFileHeader(file, magic_number)
    if not cfh_header.f_flags & 0x2000:
        log_msg('Did not change rpath since not a shared library/archive')
        return
    # Read auxiliary header
    aux_header = XcoffAuxiliaryHeader(file, magic_number, cfh_header.f_opthdr)

    # Calculate the bytes_to_align
    bytes_to_align = max(aux_header.o_algntext, aux_header.o_algndata)

    # Seek to section header and read it
    if magic_number == 0x01DF:
        file.seek((aux_header.o_snloader - 1) * XcoffSectionHeader.SCN_HDR_SIZE_32, os.SEEK_CUR)
    else:
        file.seek((aux_header.o_snloader - 1) * XcoffSectionHeader.SCN_HDR_SIZE, os.SEEK_CUR)
    try:
        scn_header = XcoffSectionHeader(file, magic_number)
    except EOFError:
        return  # End of archive member, nothing to fix

    header_len = 0
    if ar_header:
        header_len = XcoffFixedLengthHeader.FL_HDR_SIZE + XcoffArchiveHeader.AR_HDR_SIZE + ar_header.ar_namlen
        scnptrFromArchiveStart = scn_header.s_scnptr + align(header_len, bytes_to_align)
    else:
        scnptrFromArchiveStart = scn_header.s_scnptr

    file.seek(scnptrFromArchiveStart)

    # Read loader header
    ldr_header = XcoffLoaderHeader(file, magic_number)

    if ar_header:
        scnptrFromArchiveStartPlusOff = scn_header.s_scnptr + ldr_header.l_impoff + align(header_len, bytes_to_align)
    else:
        scnptrFromArchiveStartPlusOff = scn_header.s_scnptr + ldr_header.l_impoff
    file.seek(scnptrFromArchiveStartPlusOff)

    # Read and update libpath
    libpath = file.read(ldr_header.l_istlen)
    build_libpath = libpath.split(b'\x00')[0]
    # Build the new rpath by merging new_rpath with existing paths (excluding removed ones)
    new_rpaths: OrderedSet[bytes] = OrderedSet()
    if new_rpath:
        new_rpaths.update(new_rpath.split(b':'))

    new_rpaths.update(
        path
        for path in build_libpath.split(b':')
        if path and path not in rpath_dirs_to_remove
    )

    install_rpath = b':'.join(new_rpaths)

    # If the length of the build_rpath length is < install_rpath length then we do not have space to write
    # the same hence exit. Otherwise, we can and the length has to be the same as build_rpath.
    # If the install_rpath length is less than build_rpath length then pad the difference
    if len(install_rpath) > len(build_libpath):
        sys.exit('Error: install_rpath is bigger than build_rpath')
    # Pad with colon bytes to match build_libpath length
    install_rpath = install_rpath + (b':' * (len(build_libpath) - len(install_rpath)))
    file.seek(scnptrFromArchiveStartPlusOff)
    file.write(install_rpath)
    log_msg(f'Successfully changed libpath from {build_libpath!r} to {install_rpath!r}')


def fix_aix(fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: T.Optional[bytes], verbose: bool = True) -> None:
    """Writes Libpath to an xcoff shared object.

    In AIX, shared modules are .so files and shared libraries are in .a archives.
    Follows the same calling convention as fix_elf:
    - Errors: sys.exit('error message')
    - Wrong file type: sys.exit(0)
    - Success: return normally
    """
    if new_rpath is None:
        return

    try:
        with open(fname, 'r+b') as file:
            traverse_xcoff(file, rpath_dirs_to_remove, new_rpath, verbose)
    except FileNotFoundError:
        sys.exit(f'Error: File not found: {fname}')
    except Exception as e:
        sys.exit(f'Unexpected error processing {fname}: {e}')


# ----------------ELF------------------

class DataSizes:
    def __init__(self, ptrsize: int, is_le: bool) -> None:
        if is_le:
            p = '<'
        else:
            p = '>'
        self.Char = p + 'c'
        self.CharSize = 1
        self.Half = p + 'h'
        self.HalfSize = 2
        self.Section = p + 'h'
        self.SectionSize = 2
        self.Word = p + 'I'
        self.WordSize = 4
        self.Sword = p + 'i'
        self.SwordSize = 4
        if ptrsize == 64:
            self.Addr = p + 'Q'
            self.AddrSize = 8
            self.Off = p + 'Q'
            self.OffSize = 8
            self.XWord = p + 'Q'
            self.XWordSize = 8
            self.Sxword = p + 'q'
            self.SxwordSize = 8
        else:
            self.Addr = p + 'I'
            self.AddrSize = 4
            self.Off = p + 'I'
            self.OffSize = 4

class DynamicEntry(DataSizes):
    def __init__(self, ifile: T.BinaryIO, ptrsize: int, is_le: bool) -> None:
        super().__init__(ptrsize, is_le)
        self.ptrsize = ptrsize
        if ptrsize == 64:
            self.d_tag = struct.unpack(self.Sxword, ifile.read(self.SxwordSize))[0]
            self.val = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.d_tag = struct.unpack(self.Sword, ifile.read(self.SwordSize))[0]
            self.val = struct.unpack(self.Word, ifile.read(self.WordSize))[0]

    def write(self, ofile: T.BinaryIO) -> None:
        if self.ptrsize == 64:
            ofile.write(struct.pack(self.Sxword, self.d_tag))
            ofile.write(struct.pack(self.XWord, self.val))
        else:
            ofile.write(struct.pack(self.Sword, self.d_tag))
            ofile.write(struct.pack(self.Word, self.val))

class DynsymEntry(DataSizes):
    def __init__(self, ifile: T.BinaryIO, ptrsize: int, is_le: bool) -> None:
        super().__init__(ptrsize, is_le)
        is_64 = ptrsize == 64
        self.st_name = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
        if is_64:
            self.st_info = struct.unpack(self.Char, ifile.read(self.CharSize))[0]
            self.st_other = struct.unpack(self.Char, ifile.read(self.CharSize))[0]
            self.st_shndx = struct.unpack(self.Section, ifile.read(self.SectionSize))[0]
            self.st_value = struct.unpack(self.Addr, ifile.read(self.AddrSize))[0]
            self.st_size = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.st_value = struct.unpack(self.Addr, ifile.read(self.AddrSize))[0]
            self.st_size = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
            self.st_info = struct.unpack(self.Char, ifile.read(self.CharSize))[0]
            self.st_other = struct.unpack(self.Char, ifile.read(self.CharSize))[0]
            self.st_shndx = struct.unpack(self.Section, ifile.read(self.SectionSize))[0]

class SectionHeader(DataSizes):
    def __init__(self, ifile: T.BinaryIO, ptrsize: int, is_le: bool) -> None:
        super().__init__(ptrsize, is_le)
        is_64 = ptrsize == 64

# Elf64_Word
        self.sh_name = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Word
        self.sh_type = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Xword
        if is_64:
            self.sh_flags = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.sh_flags = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Addr
        self.sh_addr = struct.unpack(self.Addr, ifile.read(self.AddrSize))[0]
# Elf64_Off
        self.sh_offset = struct.unpack(self.Off, ifile.read(self.OffSize))[0]
# Elf64_Xword
        if is_64:
            self.sh_size = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.sh_size = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Word
        self.sh_link = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Word
        self.sh_info = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Xword
        if is_64:
            self.sh_addralign = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.sh_addralign = struct.unpack(self.Word, ifile.read(self.WordSize))[0]
# Elf64_Xword
        if is_64:
            self.sh_entsize = struct.unpack(self.XWord, ifile.read(self.XWordSize))[0]
        else:
            self.sh_entsize = struct.unpack(self.Word, ifile.read(self.WordSize))[0]

class Elf(DataSizes):
    def __init__(self, bfile: str, verbose: bool = True) -> None:
        self.bfile = bfile
        self.verbose = verbose
        self.sections: T.List[SectionHeader] = []
        self.dynamic: T.List[DynamicEntry] = []
        self.dynsym: T.List[DynsymEntry] = []
        self.dynsym_strings: T.List[str] = []
        self.open_bf(bfile)
        try:
            (self.ptrsize, self.is_le) = self.detect_elf_type()
            super().__init__(self.ptrsize, self.is_le)
            self.parse_header()
            self.parse_sections()
            self.parse_dynamic()
            self.parse_dynsym()
            self.parse_dynsym_strings()
        except (struct.error, RuntimeError):
            self.close_bf()
            raise

    def open_bf(self, bfile: str) -> None:
        self.bf = None
        self.bf_perms = None
        try:
            self.bf = open(bfile, 'r+b')
        except PermissionError as e:
            self.bf_perms = stat.S_IMODE(os.lstat(bfile).st_mode)
            os.chmod(bfile, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
            try:
                self.bf = open(bfile, 'r+b')
            except Exception:
                os.chmod(bfile, self.bf_perms)
                self.bf_perms = None
                raise e

    def close_bf(self) -> None:
        if self.bf is not None:
            if self.bf_perms is not None:
                os.chmod(self.bf.fileno(), self.bf_perms)
                self.bf_perms = None
            self.bf.close()
            self.bf = None

    def __enter__(self) -> 'Elf':
        return self

    def __del__(self) -> None:
        self.close_bf()

    def __exit__(self, exc_type: T.Any, exc_value: T.Any, traceback: T.Any) -> None:
        self.close_bf()

    def detect_elf_type(self) -> T.Tuple[int, bool]:
        data = self.bf.read(6)
        if data[1:4] != b'ELF':
            # This script gets called to non-elf targets too
            # so just ignore them.
            if self.verbose:
                print(f'File {self.bfile!r} is not an ELF file.')
            sys.exit(0)
        if data[4] == 1:
            ptrsize = 32
        elif data[4] == 2:
            ptrsize = 64
        else:
            sys.exit(f'File {self.bfile!r} has unknown ELF class.')
        if data[5] == 1:
            is_le = True
        elif data[5] == 2:
            is_le = False
        else:
            sys.exit(f'File {self.bfile!r} has unknown ELF endianness.')
        return ptrsize, is_le

    def parse_header(self) -> None:
        self.bf.seek(0)
        self.e_ident = struct.unpack('16s', self.bf.read(16))[0]
        self.e_type = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_machine = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_version = struct.unpack(self.Word, self.bf.read(self.WordSize))[0]
        self.e_entry = struct.unpack(self.Addr, self.bf.read(self.AddrSize))[0]
        self.e_phoff = struct.unpack(self.Off, self.bf.read(self.OffSize))[0]
        self.e_shoff = struct.unpack(self.Off, self.bf.read(self.OffSize))[0]
        self.e_flags = struct.unpack(self.Word, self.bf.read(self.WordSize))[0]
        self.e_ehsize = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_phentsize = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_phnum = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_shentsize = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_shnum = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]
        self.e_shstrndx = struct.unpack(self.Half, self.bf.read(self.HalfSize))[0]

    def parse_sections(self) -> None:
        self.bf.seek(self.e_shoff)
        for _ in range(self.e_shnum):
            self.sections.append(SectionHeader(self.bf, self.ptrsize, self.is_le))

    def read_str(self) -> bytes:
        arr = []
        x = self.bf.read(1)
        while x != b'\0':
            arr.append(x)
            x = self.bf.read(1)
            if x == b'':
                raise RuntimeError('Tried to read past the end of the file')
        return b''.join(arr)

    def find_section(self, target_name: bytes) -> T.Optional[SectionHeader]:
        section_names = self.sections[self.e_shstrndx]
        for i in self.sections:
            self.bf.seek(section_names.sh_offset + i.sh_name)
            name = self.read_str()
            if name == target_name:
                return i
        return None

    def parse_dynamic(self) -> None:
        sec = self.find_section(b'.dynamic')
        if sec is None:
            return
        self.bf.seek(sec.sh_offset)
        while True:
            e = DynamicEntry(self.bf, self.ptrsize, self.is_le)
            self.dynamic.append(e)
            if e.d_tag == 0:
                break

    def parse_dynsym(self) -> None:
        sec = self.find_section(b'.dynsym')
        if sec is None:
            return
        self.bf.seek(sec.sh_offset)
        for i in range(sec.sh_size // sec.sh_entsize):
            e = DynsymEntry(self.bf, self.ptrsize, self.is_le)
            self.dynsym.append(e)

    def parse_dynsym_strings(self) -> None:
        sec = self.find_section(b'.dynstr')
        if sec is None:
            return
        for i in self.dynsym:
            self.bf.seek(sec.sh_offset + i.st_name)
            self.dynsym_strings.append(self.read_str().decode())

    @generate_list
    def get_section_names(self) -> T.Generator[str, None, None]:
        section_names = self.sections[self.e_shstrndx]
        for i in self.sections:
            self.bf.seek(section_names.sh_offset + i.sh_name)
            yield self.read_str().decode()

    def get_soname(self) -> T.Optional[str]:
        soname = None
        strtab = None
        for i in self.dynamic:
            if i.d_tag == DT_SONAME:
                soname = i
            if i.d_tag == DT_STRTAB:
                strtab = i
        if soname is None or strtab is None:
            return None
        self.bf.seek(strtab.val + soname.val)
        return self.read_str().decode()

    def get_entry_offset(self, entrynum: int) -> T.Optional[int]:
        sec = self.find_section(b'.dynstr')
        for i in self.dynamic:
            if i.d_tag == entrynum:
                res = sec.sh_offset + i.val
                assert isinstance(res, int)
                return res
        return None

    def get_rpath(self) -> T.Optional[str]:
        offset = self.get_entry_offset(DT_RPATH)
        if offset is None:
            return None
        self.bf.seek(offset)
        return self.read_str().decode()

    def get_runpath(self) -> T.Optional[str]:
        offset = self.get_entry_offset(DT_RUNPATH)
        if offset is None:
            return None
        self.bf.seek(offset)
        return self.read_str().decode()

    @generate_list
    def get_deps(self) -> T.Generator[str, None, None]:
        sec = self.find_section(b'.dynstr')
        for i in self.dynamic:
            if i.d_tag == DT_NEEDED:
                offset = sec.sh_offset + i.val
                self.bf.seek(offset)
                yield self.read_str().decode()

    def fix_deps(self, prefix: bytes) -> None:
        sec = self.find_section(b'.dynstr')
        deps = []
        for i in self.dynamic:
            if i.d_tag == DT_NEEDED:
                deps.append(i)
        for i in deps:
            offset = sec.sh_offset + i.val
            self.bf.seek(offset)
            name = self.read_str()
            if name.startswith(prefix):
                basename = name.rsplit(b'/', maxsplit=1)[-1]
                padding = b'\0' * (len(name) - len(basename))
                newname = basename + padding
                assert len(newname) == len(name)
                self.bf.seek(offset)
                self.bf.write(newname)

    def fix_rpath(self, fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: bytes) -> None:
        # The path to search for can be either rpath or runpath.
        # Fix both of them to be sure.
        self.fix_rpathtype_entry(fname, rpath_dirs_to_remove, new_rpath, DT_RPATH)
        self.fix_rpathtype_entry(fname, rpath_dirs_to_remove, new_rpath, DT_RUNPATH)

    def fix_rpathtype_entry(self, fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: bytes, entrynum: int) -> None:
        rp_off = self.get_entry_offset(entrynum)
        if rp_off is None:
            if self.verbose:
                print(f'File {fname!r} does not have an rpath. It should be a fully static executable.')
            return
        self.bf.seek(rp_off)

        old_rpath = self.read_str()
        # Some rpath entries may come from multiple sources.
        # Only add each one once.
        new_rpaths: OrderedSet[bytes] = OrderedSet()
        if new_rpath:
            new_rpaths.update(new_rpath.split(b':'))
        if old_rpath:
            # Filter out build-only rpath entries
            # added by get_link_dep_subdirs() or
            # specified by user with build_rpath.
            for rpath_dir in old_rpath.split(b':'):
                if not (rpath_dir in rpath_dirs_to_remove or
                        rpath_dir == (b'X' * len(rpath_dir))):
                    if rpath_dir:
                        new_rpaths.add(rpath_dir)

        # Prepend user-specified new entries while preserving the ones that came from pkgconfig etc.
        new_rpath = b':'.join(new_rpaths)

        if len(old_rpath) < len(new_rpath):
            msg = 'New rpath must not be longer than the old one.\n Old: {}\n New: {}'.format(old_rpath.decode('utf-8'), new_rpath.decode('utf-8'))
            sys.exit(msg)
        # The linker does read-only string deduplication. If there is a
        # string that shares a suffix with the rpath, they might get
        # deduped. This means changing the rpath string might break something
        # completely unrelated. This has already happened once with X.org.
        # Thus we want to keep this change as small as possible to minimize
        # the chance of obliterating other strings. It might still happen
        # but our behavior is identical to what chrpath does and it has
        # been in use for ages so based on that this should be rare.
        if not new_rpath:
            self.remove_rpath_entry(entrynum)
        else:
            self.bf.seek(rp_off)
            self.bf.write(new_rpath)
            self.bf.write(b'\0')

    def clean_rpath_entry_string(self, entrynum: int) -> None:
        # Get the rpath string
        offset = self.get_entry_offset(entrynum)
        self.bf.seek(offset)
        rpath_string = self.read_str().decode()
        reused_str = ''

        # Inspect the dyn strings and check if our rpath string
        # ends with one of them.
        # This is to handle a subtle optimization of the linker
        # where one of the dyn function name offset in the dynstr
        # table might be set at the an offset of the rpath string.
        # Example:
        #
        # rpath        offset = 1314 string = /usr/lib/foo
        # dym function offset = 1322 string = foo
        #
        # In the following case, the dym function string offset is
        # placed at the offset +10 of the rpath.
        # To correctly clear the rpath entry AND keep normal
        # functionality of this optimization (and the binary),
        # parse the maximum string we can remove from the rpath entry.
        #
        # Since strings MUST be null terminated, we can always check
        # if the rpath string ends with the dyn function string and
        # calculate what we can actually remove accordingly.
        for dynsym_string in self.dynsym_strings:
            if rpath_string.endswith(dynsym_string):
                if len(dynsym_string) > len(reused_str):
                    reused_str = dynsym_string

        # Seek back to start of string
        self.bf.seek(offset)
        self.bf.write(b'X' * (len(rpath_string) - len(reused_str)))

    def remove_rpath_entry(self, entrynum: int) -> None:
        sec = self.find_section(b'.dynamic')
        if sec is None:
            return None
        for (i, entry) in enumerate(self.dynamic):
            if entry.d_tag == entrynum:
                self.clean_rpath_entry_string(entrynum)
                rpentry = self.dynamic[i]
                rpentry.d_tag = 0
                self.dynamic = self.dynamic[:i] + self.dynamic[i + 1:] + [rpentry]
                break
        # DT_MIPS_RLD_MAP_REL is relative to the offset of the tag. Adjust it consequently.
        for entry in self.dynamic[i:]:
            if entry.d_tag == DT_MIPS_RLD_MAP_REL:
                entry.val += 2 * (self.ptrsize // 8)
                break
        self.bf.seek(sec.sh_offset)
        for entry in self.dynamic:
            entry.write(self.bf)
        return None

def fix_elf(fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: T.Optional[bytes], verbose: bool = True) -> None:
    if new_rpath is not None:
        with Elf(fname, verbose) as e:
            # note: e.get_rpath() and e.get_runpath() may be useful
            e.fix_rpath(fname, rpath_dirs_to_remove, new_rpath)

def get_darwin_rpaths(fname: str) -> OrderedSet[str]:
    p, out, _ = Popen_safe(['otool', '-l', fname], stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, p.args, out)
    # Need to deduplicate rpaths, as macOS's install_name_tool
    # is *very* allergic to duplicate -delete_rpath arguments
    # when calling depfixer on installation.
    result: OrderedSet[str] = OrderedSet()
    current_cmd = 'FOOBAR'
    for line in out.split('\n'):
        line = line.strip()
        if ' ' not in line:
            continue
        key, value = line.strip().split(' ', 1)
        if key == 'cmd':
            current_cmd = value
        if key == 'path' and current_cmd == 'LC_RPATH':
            rp = value.split('(', 1)[0].strip()
            result.add(rp)
    return result

def fix_darwin(fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: str, final_path: str, install_name_mappings: T.Dict[str, str]) -> None:
    try:
        old_rpaths = get_darwin_rpaths(fname)
    except subprocess.CalledProcessError:
        # Otool failed, which happens when invoked on a
        # non-executable target. Just return.
        return
    new_rpaths: OrderedSet[str] = OrderedSet()
    if new_rpath:
        new_rpaths.update(new_rpath.split(':'))
    # filter out build-only rpath entries, like in
    # fix_rpathtype_entry
    remove_rpaths = [x.decode('utf8') for x in rpath_dirs_to_remove]
    for rpath_dir in old_rpaths:
        if rpath_dir and rpath_dir not in remove_rpaths:
            new_rpaths.add(rpath_dir)
    try:
        args = []
        # compute diff, translate it into -delete_rpath and -add_rpath
        # calls
        for path in new_rpaths:
            if path not in old_rpaths:
                args += ['-add_rpath', path]
        for path in old_rpaths:
            if path not in new_rpaths:
                args += ['-delete_rpath', path]
        # Rewrite -install_name @rpath/libfoo.dylib to /path/to/libfoo.dylib
        if fname.endswith('dylib'):
            args += ['-id', final_path]
        if install_name_mappings:
            for old, new in install_name_mappings.items():
                args += ['-change', old, new]
        if args:
            subprocess.check_call(['install_name_tool', fname] + args,
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
    except Exception as err:
        raise SystemExit(err)

def fix_jar(fname: str) -> None:
    subprocess.check_call(['jar', 'xf', fname, 'META-INF/MANIFEST.MF'])
    with open('META-INF/MANIFEST.MF', 'r+', encoding='utf-8') as f:
        lines = f.readlines()
        f.seek(0)
        for line in lines:
            if not line.startswith('Class-Path:'):
                f.write(line)
        f.truncate()
    # jar -um doesn't allow removing existing attributes.  Use -uM instead,
    # which a) removes the existing manifest from the jar and b) disables
    # special-casing for the manifest file, so we can re-add it as a normal
    # archive member.  This puts the manifest at the end of the jar rather
    # than the beginning, but the spec doesn't forbid that.
    subprocess.check_call(['jar', 'ufM', fname, 'META-INF/MANIFEST.MF'])

def fix_rpath(fname: str, rpath_dirs_to_remove: T.Set[bytes], new_rpath: T.Union[str, bytes], final_path: str, install_name_mappings: T.Dict[str, str], system: str, verbose: bool = True) -> None:
    global INSTALL_NAME_TOOL  # pylint: disable=global-statement
    # Static libraries, import libraries, debug information, headers, etc
    # never have rpaths
    # DLLs and EXE currently do not need runtime path fixing

    if fname.endswith(('.lib', '.pdb', '.h', '.hpp', '.dll', '.exe')):
        return
    # Shared libraries are .a files on AIX
    if fname.endswith('.a') and system != 'aix':
        return
    if isinstance(new_rpath, str):
        new_rpath = new_rpath.encode('utf8')
    try:
        if fname.endswith('.jar'):
            fix_jar(fname)
            return
        if system == 'aix':
            fix_aix(fname, rpath_dirs_to_remove, new_rpath, verbose)
        else:
            fix_elf(fname, rpath_dirs_to_remove, new_rpath, verbose)
        return
    except SystemExit as e:
        if isinstance(e.code, int) and e.code == 0:
            pass
        else:
            raise
    # We don't look for this on import because it will do a useless PATH lookup
    # on non-mac platforms. That can be expensive on some Windows machines
    # (up to 30ms), which is significant with --only-changed. For details, see:
    # https://github.com/mesonbuild/meson/pull/6612#discussion_r378581401
    if INSTALL_NAME_TOOL is False:
        INSTALL_NAME_TOOL = bool(shutil.which('install_name_tool'))
    if INSTALL_NAME_TOOL:
        if isinstance(new_rpath, bytes):
            new_rpath = new_rpath.decode('utf8')
        fix_darwin(fname, rpath_dirs_to_remove, new_rpath, final_path, install_name_mappings)
