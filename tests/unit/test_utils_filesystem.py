import io
import sys
import tarfile

import pytest

import tmt.utils.filesystem
from tmt.utils import GeneralError

# Extraction filters are available since Python 3.12.4
FILTERS_SUPPORTED = sys.version_info >= (3, 12, 4)


def create_archive(path, members: dict[str, bytes]) -> None:
    """Create a gzipped tar archive with the given members"""

    with tarfile.open(path, 'w:gz') as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))


def test_unpack_archive(tmp_path):
    """Regular members are extracted into the destination directory"""

    archive = tmp_path / 'archive.tar.gz'
    create_archive(archive, {'directory/file.txt': b'hello world'})

    tmt.utils.filesystem.unpack_archive(archive, tmp_path / 'destination')

    assert (tmp_path / 'destination' / 'directory' / 'file.txt').read_bytes() == b'hello world'


@pytest.mark.skipif(
    not FILTERS_SUPPORTED,
    reason='extraction filters require Python 3.12.4+',
)
def test_unpack_archive_rejects_path_traversal(tmp_path):
    """Members escaping the destination directory are rejected"""

    archive = tmp_path / 'archive.tar.gz'
    create_archive(
        archive,
        {
            'innocent.txt': b'hello world',
            '../../../escape.txt': b'pwned',
        },
    )

    with pytest.raises(GeneralError, match='outside the destination'):
        tmt.utils.filesystem.unpack_archive(archive, tmp_path / 'destination')

    assert not (tmp_path / 'escape.txt').exists()
    assert not (tmp_path.parent / 'escape.txt').exists()


@pytest.mark.skipif(
    not FILTERS_SUPPORTED,
    reason='extraction filters require Python 3.12.4+',
)
def test_unpack_archive_sanitizes_absolute_paths(tmp_path):
    """Absolute member paths are extracted inside the destination"""

    archive = tmp_path / 'archive.tar.gz'
    create_archive(archive, {'/absolute/file.txt': b'hello world'})

    tmt.utils.filesystem.unpack_archive(archive, tmp_path / 'destination')

    # Leading slashes are stripped, the member lands inside the destination
    assert (tmp_path / 'destination' / 'absolute' / 'file.txt').read_bytes() == b'hello world'
