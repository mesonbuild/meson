from pathlib import Path
import typing as T

from .core import MesonException

if T.TYPE_CHECKING:
    from io import BufferedReader

MAGIC = b'!<arch>\n'
HEADER_SIZE = 60

def _read_header(f: 'BufferedReader') -> T.Tuple[bytes, int]:
    header = f.read(HEADER_SIZE)
    if len(header) < HEADER_SIZE:
        return None, None
    file_id = header[0:16].rstrip()
    file_size = int(header[48:58])
    return file_id, file_size

def _read_data(f: 'BufferedReader', file_size: int) -> bytes:
    file_data = f.read(file_size)
    if file_size % 2 == 1:
        f.read(1)
    return file_data

def _skip_data(f: 'BufferedReader', file_size: int) -> None:
    if file_size % 2 == 1:
        file_size += 1
    f.seek(file_size, 1)

def extract(archive_filename: str, outdir: str = '.', dry_run: bool = False) -> T.List[str]:
    with open(archive_filename, 'rb') as f:
        if f.read(len(MAGIC)) != MAGIC:
            raise MesonException(f'{archive_filename} does not seems to be a static library')
        outpath = Path(outdir)
        if not dry_run:
            outpath.mkdir(exist_ok=True)
        files = []
        file_id_table = {}
        unique_id = 0
        while True:
            file_id, file_size = _read_header(f)
            if file_id is None:
                break
            elif file_id == b'/':
                # Skip symbols table.
                _skip_data(f, file_size)
                continue
            elif file_id == b'//':
                # GNU variant: extended filenames table.
                file_data = _read_data(f, file_size)
                start = 0
                for i, c in enumerate(file_data):
                    if c == ord('\n'):
                        file_id_table[start] = file_data[start:i]
                        start = i + 1
                continue
            elif file_id.startswith(b'/'):
                # GNU variant: file_id is an index into the table.
                idx = int(file_id[1:])
                file_id = file_id_table[idx]
            elif file_id.startswith(b'#1/'):
                # BSD variant: extended filename is prepended to the file data.
                id_len = int(file_id[3:])
                file_id = f.read(id_len).rstrip(b'\x00')
                file_size -= id_len

            if file_id[-1] == ord('/'):
                file_id = file_id[:-1]

            if file_id.startswith(b'__.SYMDEF'):
                # BSD variant: Skip symbols table.
                _skip_data(f, file_size)
                continue

            fname = f'{unique_id}-{file_id.decode()}'
            unique_id += 1
            files.append(fname)

            if dry_run:
                _skip_data(f, file_size)
            else:
                file_data = _read_data(f, file_size)
                output = outpath / fname
                with output.open('wb') as ofile:
                    ofile.write(file_data)

        return files
