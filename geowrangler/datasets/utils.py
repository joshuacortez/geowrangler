# AUTOGENERATED! DO NOT EDIT! File to edit: notebooks/notebooks/13_datasets_utils.ipynb (unless otherwise specified).

__all__ = ["urlretrieve", "make_report_hook"]

# Internal Cell

import contextlib
from urllib.error import ContentTooShortError
from urllib.parse import urlparse

from fastcore.net import urlopen
from fastprogress.fastprogress import progress_bar
from loguru import logger

# Cell
# from https://github.com/fastai/fastcore/blob/86337bad16a65f23c5335286ab73cd4d6425c586/fastcore/net.py#L147
# add headers to urlwrap call (to allow auth)
def urlretrieve(
    url, filename, headers=None, reporthook=None, timeout=None, chunksize=8192
):
    "Same as `urllib.request.urlretrieve` but also works with `Request` objects"
    with contextlib.closing(
        urlopen(url, data=None, headers=headers, timeout=timeout)
    ) as fp:
        respheaders = fp.info()
        logger.info(f"Retrieving {url} into {filename}")
        with open(filename, "wb") as tfp:
            size = -1
            read = 0
            blocknum = 0
            if "Content-length" in respheaders:
                size = int(respheaders["Content-Length"])
                if size < chunksize:
                    chunksize = size
            if reporthook:
                reporthook(blocknum, chunksize, size)
            while True:
                block = fp.read(chunksize)
                if not block:
                    break
                read += len(block)
                tfp.write(block)
                blocknum += 1
                if reporthook:
                    reporthook(blocknum, chunksize, size)

    if size >= 0 and read < size:
        raise ContentTooShortError(
            f"retrieval incomplete: got only {read} out of {size} bytes", respheaders
        )
    return filename, respheaders, fp


# Cell
def make_report_hook(show_progress):
    if not show_progress:
        return None
    pbar = progress_bar([])

    def progress(count=1, bsize=1, tsize=None):
        pbar.total = tsize
        pbar.update(count * bsize)

    return progress
