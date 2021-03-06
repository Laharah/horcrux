import pytest
import random
import sys
import rich
from pathlib import Path

from horcrux import cli


@pytest.fixture(autouse=True)
def rich_reset():
    "reset the rich console after each test"
    try:
        yield
    finally:
        rich._console = None


def test_parse():
    args = cli._parse(["split", "-", "test", "2", "6"])
    assert args.n == 6
    assert args.threshold == 2
    assert args.in_file == "-"
    assert args.output_dir == Path("test")
    with pytest.raises(SystemExit):
        args = cli._parse("split - test two 5".split())
    args = cli._parse("split my_file 2 5".split())
    assert args.in_file == "my_file"
    assert args.cmd == "split"


def test_parse_combine(tmp_path):
    args = cli._resolve_files_combine(
        cli._parse(["combine", "a", "b", "c", "--output", str(tmp_path)])
    )
    assert args.in_files == [Path(p) for p in "a b c".split()]
    assert args.output_dir == tmp_path
    assert args.output_filename == None
    args = cli._resolve_files_combine(
        cli._parse(
            ["combine", "a", "b", "c", "--output", str(tmp_path / "newname.txt")]
        )
    )
    assert args.output_dir == tmp_path
    assert args.output_filename == "newname.txt"


def test_resolve_files_split(tmp_path, capfd):
    args = cli._resolve_files_split(cli._parse(["split", "-", "2", "6"]))
    assert args.in_file == sys.stdin.buffer
    assert args.file_size == None
    with pytest.raises(FileNotFoundError):
        args = cli._resolve_files_split(cli._parse(["split", "my_file.txt", "2", "6"]))
    _, err = capfd.readouterr()
    with pytest.raises(TypeError) as e:
        args = cli._resolve_files_split(cli._parse(["split", str(tmp_path), "2", "6"]))
    _, err = capfd.readouterr()
    assert "must be a file" in str(e)
    md = tmp_path / "my_data.txt"
    md.write_bytes(b"0123456789")
    args = cli._resolve_files_split(cli._parse(["split", str(md), "2", "6"]))
    assert args.in_file == md
    assert args.file_size == 10
    assert args.filename == md.name


def test_resolve_output(tmp_path):
    args = cli._resolve_files_split(
        cli._parse(["split", "-", str(tmp_path / "newhx"), "2", "5"])
    )
    assert args.horcrux_title == "newhx"
    assert args.output_dir == tmp_path
    args = cli._resolve_files_split(cli._parse(["split", "-", str(tmp_path), "2", "5"]))
    assert args.horcrux_title == None
    assert args.output_dir == tmp_path
    my_file = tmp_path / "my_file.txt"
    my_file.touch()
    args = cli._resolve_files_split(
        cli._parse(["split", str(my_file), str(tmp_path), "2", "5"])
    )
    assert args.horcrux_title == "my_file"
    assert args.output_dir == tmp_path
    args = cli._resolve_files_split(
        cli._parse(["split", str(my_file), str(tmp_path / "test"), "2", "5"])
    )
    assert args.horcrux_title == "test"
    assert args.output_dir == tmp_path
    assert args.filename == "my_file.txt"


def test_round_trip(tmp_path, capfdbinary):
    my_file = tmp_path / "my_file.txt"
    original_data = bytearray(i % 256 for i in range(10000))
    my_file.write_bytes(original_data)

    args = ["split", str(my_file), str(tmp_path / "horcrux"), "2", "4"]
    cli.main(args)
    my_file.unlink()
    for i in range(1, 4):
        assert (tmp_path / f"horcrux_{i}.hrcx").exists()

    args = ["combine"] + [str(p) for p in tmp_path.iterdir()]
    args += ["--output", str(tmp_path)]
    cli.main(args)
    assert (tmp_path / "my_file.txt").read_bytes() == original_data
    (tmp_path / "my_file.txt").unlink()
    args = ["combine"] + [str(p) for p in tmp_path.iterdir()]
    args += ["--output", "-"]
    cli.main(args)
    assert capfdbinary.readouterr()[0] == original_data
    args = ["combine"] + [str(p) for p in tmp_path.iterdir()]
    args += ["--output", str(tmp_path / "newfile.txt")]
    cli.main(args)
    assert (tmp_path / "newfile.txt").read_bytes() == original_data


def test_no_overwrite(tmp_path, capfd, monkeypatch):
    prev_file = tmp_path / "prev_file.txt"
    prev_file.write_bytes(b"\xff" * 10000)
    args = ["split", str(prev_file), str(tmp_path / "hx"), "2", "2"]
    cli.main(args)
    prev_file.write_bytes(b"\x00" * 10)
    args = [
        "combine",
        str(tmp_path / "hx_1.hrcx"),
        str(tmp_path / "hx_2.hrcx"),
        "--output",
        str(tmp_path),
    ]
    monkeypatch.setattr("builtins.input", lambda: "n")
    cli.main(args)
    assert prev_file.read_bytes() == b"\x00" * 10
    assert "overwrite" in capfd.readouterr()[1].lower()
    monkeypatch.setattr("builtins.input", lambda: "y")
    cli.main(args)
    assert prev_file.read_bytes() == b"\xff" * 10000
    assert "overwrite" in capfd.readouterr()[1].lower()
    prev_file.unlink()
    cli.main(args)
    assert prev_file.read_bytes() == b"\xff" * 10000
    assert "overwrite" not in capfd.readouterr()[1].lower()
    args.extend(["--overwrite"])
    cli.main(args)
    assert prev_file.read_bytes() == b"\xff" * 10000
    assert "overwrite" not in capfd.readouterr()[1].lower()
