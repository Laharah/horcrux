import pytest
import random
import sys
from pathlib import Path

from horcrux import cli


def test_parse():
    args = cli._parse(['split', '6', '2', '-', 'test'])
    assert args.n == 6
    assert args.threshold == 2
    assert args.in_file == '-'
    assert args.output_dir == Path('test')
    with pytest.raises(SystemExit):
        args = cli._parse('split 5 two - test'.split())
    args = cli._parse('split 5 2 my_file'.split())
    assert args.in_file == 'my_file'
    assert args.cmd == 'split'


def test_parse_combine(tmp_path):
    args = cli._resolve_files_combine(
        cli._parse(['combine', 'a', 'b', 'c', '--output',
                    str(tmp_path)]))
    assert args.in_files == [Path(p) for p in 'a b c'.split()]
    assert args.output_dir == tmp_path
    assert args.output_filename == None
    args = cli._resolve_files_combine(
        cli._parse(['combine', 'a', 'b', 'c', '--output',
                    str(tmp_path / 'newname.txt')]))
    assert args.output_dir == tmp_path
    assert args.output_filename == 'newname.txt'


def test_resolve_files_split(tmp_path, capfd):
    args = cli._resolve_files_split(cli._parse(['split', '6', '2', '-']))
    assert args.in_file == sys.stdin.buffer
    assert args.file_size == None
    with pytest.raises(SystemExit):
        args = cli._resolve_files_split(cli._parse(['split', '6', '2', 'my_file.txt']))
    _, err = capfd.readouterr()
    assert 'not find' in err
    with pytest.raises(SystemExit):
        args = cli._resolve_files_split(cli._parse(['split', '6', '2', str(tmp_path)]))
    _, err = capfd.readouterr()
    assert 'must be a file' in err
    md = tmp_path / 'my_data.txt'
    md.write_bytes(b'0123456789')
    args = cli._resolve_files_split(cli._parse(['split', '6', '2', str(md)]))
    assert args.in_file == md
    assert args.file_size == 10
    assert args.filename == md.name


def test_resolve_output(tmp_path):
    args = cli._resolve_files_split(
        cli._parse(['split', '5', '2', '-',
                    str(tmp_path / 'newhx')]))
    assert args.horcrux_title == 'newhx'
    assert args.output_dir == tmp_path
    args = cli._resolve_files_split(cli._parse(['split', '5', '2', '-', str(tmp_path)]))
    assert args.horcrux_title == None
    assert args.output_dir == tmp_path
    my_file = tmp_path / 'my_file.txt'
    my_file.touch()
    args = cli._resolve_files_split(
        cli._parse(['split', '5', '2', str(my_file),
                    str(tmp_path)]))
    assert args.horcrux_title == 'my_file'
    assert args.output_dir == tmp_path
    args = cli._resolve_files_split(
        cli._parse(['split', '5', '2',
                    str(my_file), str(tmp_path / 'test')]))
    assert args.horcrux_title == 'test'
    assert args.output_dir == tmp_path
    assert args.filename == 'my_file.txt'


def test_round_trip(tmp_path, capfdbinary):
    my_file = tmp_path / 'my_file.txt'
    original_data = bytearray(i % 256 for i in range(10000))
    my_file.write_bytes(original_data)

    args = ['split', '4', '2', str(my_file), str(tmp_path / 'horcrux')]
    cli.main(args)
    my_file.unlink()
    for i in range(1, 4):
        assert (tmp_path / f'horcrux_{i}.hrcx').exists()

    args = ['combine']+ [str(p) for p in tmp_path.iterdir()] 
    args += ['--output', str(tmp_path)]
    cli.main(args)
    assert (tmp_path / 'my_file.txt').read_bytes() == original_data
    (tmp_path / 'my_file.txt').unlink()
    args = ['combine']+ [str(p) for p in tmp_path.iterdir()] 
    args += ['--output', '-']
    cli.main(args)
    assert capfdbinary.readouterr()[0] == original_data
    args = ['combine']+ [str(p) for p in tmp_path.iterdir()] 
    args += ['--output', str(tmp_path / 'newfile.txt')]
    cli.main(args)
    assert (tmp_path / 'newfile.txt').read_bytes() == original_data
    
