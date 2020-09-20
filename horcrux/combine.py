from typing import Sequence, List, Union
from pathlib import Path
import contextlib
import sys
from rich.progress import Progress, BarColumn, TimeRemainingColumn, FileSizeColumn

from . import io
from . import sss
from . import crypto
from .crypto import DecryptionError


def _prepare_streams(streams):
    "prepare horcruxes from input streams"
    hxs = []
    for s in streams:
        h = io.Horcrux(s)
        h.init_read()
        hxs.append(h)

    return hxs


def _init_crypto(horcruxes):
    key = sss.combine_shares([h.share for h in horcruxes])
    if horcruxes[0].encrypted_filename:
        fn = (
            crypto.SecretBox(key)
            .decrypt(horcruxes[0].encrypted_filename)
            .decode("utf8")
        )
        for h in horcruxes:
            h.encrypted_filename = fn
    c_stream = crypto.Stream()
    c_stream.init_decrypt(horcruxes[0].crypto_header, key)
    del key
    return c_stream


@contextlib.contextmanager
def _mass_open(files):
    files = [open(f, "rb") for f in files]
    try:
        yield files
    finally:
        for f in files:
            f.close()


def from_files(
    files: Sequence[io.FileLike],
    outdir: io.FileLike = ".",
    outfile_name: str = None,
    outfile=None,
    progress=False,
) -> Path:
    "combine horcruxes from filelike paths, return the new Path object"
    outdir = Path(outdir)

    with _mass_open(files) as streams:
        horcruxes = _prepare_streams(streams)
        crypto = _init_crypto(horcruxes)
        if outfile:
            from_streams(horcruxes, outfile, crypto, progress=progress)
            return outfile
        if not horcruxes[0].encrypted_filename and not outfile_name:
            # ugly, should force filename
            outfile = outdir / f"combined_horcrux_stream_{horcruxes[0].share.id.hex()}"
        elif outfile_name:
            outfile = outdir / outfile_name
        else:
            outfile = outdir / horcruxes[0].encrypted_filename
        if outfile.exists():
            resp = "x"
            while resp.lower()[0] not in "yn":
                print(f"{outfile} already exists, overwrite? (Y/n): ", file=sys.stderr)
                resp = input()
            if resp.lower()[0] == "n":
                return
        with open(outfile, "wb") as outstream:
            from_streams(horcruxes, outstream, crypto, progress=progress)
    return outfile


def from_streams(
    streams: Sequence[io.Horcrux],
    out_stream=None,
    crypto: crypto.Stream = None,
    progress=False,
) -> Union[io.IOBase, bytes]:
    "Combine horcruxes from given streams. Return the out_stream or bytes if not assigned."
    if not out_stream:
        output = io.BytesIO()
    else:
        output = out_stream
    if crypto is None:  # if crypto is provided, assume streams have been primed
        hxs = _prepare_streams(streams)
        crypto = _init_crypto(hxs)
    else:
        hxs = streams
    current_id = 0
    live = set(hxs)
    dead = set()
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        FileSizeColumn(),
        transient=True,
    ) as pb:
        task = pb.add_task("Combining...", start=False, visible=progress)

        while live:
            for h in live:
                if h.next_block_id == current_id:
                    try:
                        pt = crypto.decrypt(h.read_block()[1])
                    except DecryptionError as e:
                        e.horcrux_id = h.hrcx_id  # add some helpful info
                        raise
                    pb.update(task, advance=len(pt))
                    output.write(pt)
                    current_id += 1
                    break
                elif h.next_block_id is None:
                    dead.add(h)
                    continue
                elif h.next_block_id < current_id:
                    h.skip_block()
            live -= dead
    if not out_stream:
        return output.getvalue()
