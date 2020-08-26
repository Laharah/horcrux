"""Console script for horcrux."""
import argparse
import sys


def main():
    """Console script for horcrux."""
    parser = argparse.ArgumentParser(
        description=
        'Split a file into n encrypted horcruxes, that can only be decrypted by re-combining k of them.'
    )
    parser.add_argument('_', nargs='*')
    args = parser.parse_args()

    print("Arguments: " + str(args._))
    print("Replace this message by putting your code into " "horcrux.cli.main")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
