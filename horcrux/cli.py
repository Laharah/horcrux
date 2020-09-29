"""Console script for horcrux."""
import argparse
import sys
import os
from pathlib import Path

from . import split
from . import combine
from .sss import NotEnoughShares, IdMissMatch


def required_length(nmin, nmax):
    class RequiredLength(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            if not nmin <= len(values) <= nmax:
                msg = 'argument "{f}" requires between {nmin} and {nmax} arguments'.format(
                    f=self.dest, nmin=nmin, nmax=nmax
                )
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)

    return RequiredLength


def _parse(args=None):
    examples = """example:
    horcrux split passwords.txt ~/horcruxes 2 5
    horcrux combine ~/horcruxes/passwords_1.hrcx ~/horcruxes/passwords_4.hrcx --output -"""

    root_parser = argparse.ArgumentParser(
        "horcrux",
        description=(
            "Split a file into n encrypted horcruxes, that can only be decrypted by "
            "re-combining some number of them."
        ),
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = root_parser.add_subparsers(
        dest="cmd",
        title="Commands",
        description="Valid commands",
        help="Use `horcrux split --help` or `horcrux combine --help` for command specific arguments",
        required=True,
    )
    split_example = """examples:
    horcrux split passwords.txt ~/horcruxes 2 5
    horcrux split myfile.txt ~/horcruxes/my_hx 4 5
    tar c "Documents" | horcrux split - doc_horcrux --filename Documents.tar 2 2"""
    split_parser = subparsers.add_parser(
        "split",
        aliases=["sp", "s"],
        epilog=split_example,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    split_parser.add_argument(
        "in_file",
        metavar="INFILE",
        help='File or stream to break into horcruxes. Supports reading from stdin with "-".',
    )
    split_parser.add_argument(
        "output_dir",
        metavar="OUTPUT",
        nargs="?",
        help="Where to place created horcruxes.",
        type=Path,
        default=Path(),
    )
    split_parser.add_argument(
        "threshold",
        metavar="THRESHOLD",
        help="Number of horcrux files needed to re-assemble input.",
        type=int,
    )
    split_parser.add_argument(
        "n", metavar="N", help="Number of horcrux files to make.", type=int
    )
    split_parser.add_argument(
        "-f",
        "--filename",
        help="What to title re-assembled file. Usefull when processing streams.",
    )

    combine_example = """examples:
    horcrux combine ~/horcruxes/passwords_1.hrcx ~/horcruxes/passwords_4.hrcx
    horcrux combine my_hx_* --output=reconstructed_file.txt
    horcrux combine doc_horcrux_1.hrcx doc_horcrux_2.hrcx --output - | tar x"""
    c_parser = subparsers.add_parser(
        "combine",
        aliases=["comb", "c"],
        epilog=combine_example,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    c_parser.add_argument(
        "in_files", nargs="+", metavar="INPUT_FILES", action=required_length(2, 254)
    )
    c_parser.add_argument(
        "--output",
        nargs="?",
        metavar="OUTPUT",
        default=".",
        help="Where to place the newly reconstructed file.",
    )
    c_parser.add_argument(
        "--overwrite",
        "-f",
        action="store_true",
        help="Overwrite files without prompting",
    )
    if args is None:
        args = root_parser.parse_args()
    else:
        args = root_parser.parse_args(args)
    return args


def _resolve_files_split(args):
    # file size stuff
    if args.in_file == "-":
        args.in_file = sys.stdin.buffer
        args.file_size = None
    else:
        args.in_file = Path(args.in_file)
        if not args.in_file.exists():
            raise FileNotFoundError(f"Could not find file {args.in_file}.")
        if not args.in_file.is_file() and not args.in_file.is_fifo():
            raise TypeError("INFILE argument must be a file or pipe")
        if args.in_file.is_file():
            args.file_size = os.stat(args.in_file).st_size
            args.filename = args.in_file.name if not args.filename else args.filename
        else:
            args.file_size = None

    # output_dir and filename
    if not args.output_dir.exists():
        if args.output_dir.parent.exists():
            args.horcrux_title = args.output_dir.name
            args.output_dir = args.output_dir.parent
        else:
            print(f"Could not find directory {args.output_dir.parent}", file=sys.stderr)
    elif args.output_dir.is_dir():
        if not args.filename:
            args.horcrux_title = None
        else:
            args.horcrux_title = Path(args.filename).stem
    else:  # output_dir is filename
        args.horcrux_title = args.output_dir.name
        args.output_dir = Path()
    return args


def _resolve_files_combine(args):
    args.in_files = [Path(f) for f in args.in_files]
    if args.output == "-":
        args.output = sys.stdout.buffer
        return args
    args.output = Path(args.output)
    if args.output.is_dir():
        args.output_dir = args.output
        args.output_filename = None
    elif not args.output.exists():
        if args.output.parent.exists():
            args.output_filename = args.output.name
            args.output_dir = args.output.parent
        else:
            print(f"Could not find output direcrory {args.output}.", file=sys.stderr)
    return args


def main(args=None):
    """Console script for horcrux."""
    try:
        if args is None:
            args = _parse()
        else:
            args = _parse(args)
    except (FileNotFoundError, TypeError) as e:
        print(e, file=sys.stderr)
        return 2

    if args.cmd.startswith("s"):
        args = _resolve_files_split(args)
        if isinstance(args.in_file, Path):
            with open(args.in_file, "rb") as in_stream:
                s = split.Stream(
                    in_stream,
                    args.n,
                    args.threshold,
                    args.file_size,
                    args.filename,
                    args.output_dir,
                    args.horcrux_title,
                )
                s.init_horcruxes()
                s.distribute(progress=True)
        else:
            s = split.Stream(
                args.in_file,
                args.n,
                args.threshold,
                args.file_size,
                args.filename,
                args.output_dir,
                args.horcrux_title,
            )
            s.init_horcruxes()
            s.distribute(progress=True)
        return 0
    elif args.cmd.startswith("c"):
        args = _resolve_files_combine(args)
        try:
            if isinstance(args.output, Path):
                combine.from_files(
                    args.in_files,
                    args.output_dir,
                    args.output_filename,
                    overwrite=args.overwrite,
                    progress=True,
                )
            else:
                combine.from_files(args.in_files, outfile=args.output)
        # Catch most likely failure modes
        except (NotEnoughShares, IdMissMatch, combine.crypto.DecryptionError) as e:
            if isinstance(e, combine.DecryptionError):
                print(f"{e} Horcrux {e.horcrux_id+1} is likely corrupted.")
            else:
                print(e, file=sys.stderr)
            return 2
        return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
