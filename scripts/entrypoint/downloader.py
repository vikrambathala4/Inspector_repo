import logging
import urllib.request


def download_file(url: str, dst: str) -> bool:
    """
    Download the data at 'url' and write the data
    to a filepath specified by 'dst'.
    Returns true on success and false on failure.
    """
    try:
        urllib.request.urlretrieve(url, dst)
    except Exception as e:
        logging.error(e)
        return False

    return True
