"""
Url handling helpers.
"""

import email.message
import re

import tmt.log
import tmt.utils
from tmt.utils import Path

#: Schemes allowed when downloading files, e.g. archives fetched by the
#: discover step. Other schemes, including remote helper URLs of the
#: ``<helper>::<address>`` form, are rejected.
DOWNLOAD_URL_ALLOWED_SCHEMES: tuple[str, ...] = ('http', 'https')

DOWNLOAD_URL_REMOTE_HELPER_PATTERN: re.Pattern[str] = re.compile(r'^[a-zA-Z0-9+.-]+::')
DOWNLOAD_URL_SCHEME_PATTERN: re.Pattern[str] = re.compile(r'^([a-zA-Z0-9+.-]+)://')


def validate_download_url(url: str) -> str:
    """
    Make sure the URL can be downloaded.

    Only plain ``http`` and ``https`` URLs are allowed. Since the URL often
    comes from test metadata which may be untrusted, reject URLs using
    other schemes or remote helper transports, giving a clear error instead
    of a confusing failure of the underlying HTTP client.

    :param url: the URL to validate.
    :returns: the validated URL, unchanged.
    :raises GeneralError: when the URL cannot be downloaded.
    """

    if DOWNLOAD_URL_REMOTE_HELPER_PATTERN.match(url):
        raise tmt.utils.GeneralError(
            f"Remote helper transport is not allowed for downloading '{url}'."
        )

    scheme = DOWNLOAD_URL_SCHEME_PATTERN.match(url)
    if scheme is not None and scheme.group(1).lower() not in DOWNLOAD_URL_ALLOWED_SCHEMES:
        raise tmt.utils.GeneralError(
            f"Scheme '{scheme.group(1)}' is not allowed for downloading '{url}'. "
            f"Allowed schemes are: {', '.join(DOWNLOAD_URL_ALLOWED_SCHEMES)}."
        )

    return url


def download(url: str, destination: Path, *, logger: tmt.log.Logger) -> Path:
    logger.debug(f"Downloading '{url}'.")
    validate_download_url(url)
    with tmt.utils.retry_session(logger=logger) as session:
        response = session.get(url, stream=True)
    response.raise_for_status()
    if destination.is_dir():
        file_name = None
        if "Content-Disposition" in response.headers:
            # We use email.message to parse the Content-Disposition header since the regex can get
            # quite complicate. We do not support `filename*` with this yet, but that is even more
            # complicated to handle. Waiting on a better library to handle it.
            # See: https://stackoverflow.com/a/12017573
            _msg_handler = email.message.Message()
            _msg_handler["Content-Disposition"] = response.headers["Content-Disposition"]
            # If this one fails, it should return a None object, then try to get from url instead
            file_name = _msg_handler.get_filename()
        if not file_name:
            file_name = response.url.split("/")[-1]
    else:
        if destination.exists():
            raise tmt.utils.GeneralError(f"Destination file already exists: {destination}")
        file_name = destination.name
        destination = destination.parent
    assert isinstance(file_name, str)  # Narrow type
    download_file = destination / file_name
    with download_file.open(mode="wb") as f:
        for chunk in response.iter_content(chunk_size=None):
            f.write(chunk)
    return download_file
