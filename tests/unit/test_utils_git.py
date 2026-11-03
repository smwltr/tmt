import pytest

import tmt.utils.git
from tmt.utils import GitUrlError


@pytest.mark.parametrize(
    'url',
    [
        # Allowed schemes
        'https://example.com/repo.git',
        'http://example.com/repo.git',
        'git://example.com/repo.git',
        'git+ssh://example.com/repo.git',
        'ssh://git@example.com/repo.git',
        'ssh+git://example.com/repo.git',
        'file:///tmp/repository',
        # scp-like addresses
        'git@example.com:repo.git',
        'example.com:repo.git',
        # local paths
        '/tmp/repository',
        './repository',
        '../repository',
        'repository',
    ],
    ids=(
        'https',
        'http',
        'git',
        'git+ssh',
        'ssh',
        'ssh+git',
        'file',
        'scp-like with user',
        'scp-like',
        'absolute path',
        'relative path',
        'parent path',
        'local path',
    ),
)
def test_validate_git_url_allowed(url: str) -> None:
    """Allowed URLs are returned unchanged"""

    assert tmt.utils.git.validate_git_url(url) == url


@pytest.mark.parametrize(
    'url',
    [
        # Remote helpers, most notably 'ext::<command>', run commands
        'ext::sh -c touch /tmp/pwned',
        'EXT::sh -c touch /tmp/pwned',
        'fd::7',
        'unknown-helper::address',
        # Schemes outside of the allowlist
        'ftp://example.com/repo.git',
        'hg::http://example.com/repo',
        'transport://example.com/repo',
        # Command line option lookalikes
        '--upload-pack=touch /tmp/pwned',
    ],
    ids=(
        'ext transport',
        'ext transport, uppercase',
        'fd transport',
        'unknown helper',
        'ftp scheme',
        'hg helper with address',
        'unknown scheme',
        'option lookalike',
    ),
)
def test_validate_git_url_rejected(url: str) -> None:
    """Forbidden transports are rejected"""

    with pytest.raises(GitUrlError, match='git url'):
        tmt.utils.git.validate_git_url(url)
