# Horcrux

Split a file into n encrypted horcruxes, that can only be decrypted by re-combining k of them.

Inspired by https://github.com/kndyry/horcrux


* Free software: MIT license

## Features

* xChaCha20-poly1305 for data encryption and Samir Secret Sharing for key splitting.
* Data split evenly as possible amongst horcrux files.
* works on files or stdin streams
* memory efficient splitting and combining, virtually no file size limit.

## Requirements
* python 3.8+
* libsodium (pynacl)
* protobuf
* rich

## Installing

`pip install git+https://github.com/laharah/horcrux`

## Compiling

If you want to have a stand-alone exe of horcrux you can use pyinstaller compile one.

It's recommended that you make a virtualenv and use pip to install both horcrux and pyinstaller:

```
> mkvirtualenv temp-env
> pip install git+https://github.com/laharah/horcrux
> pip install pyinstaller
```

Once you can confirm that running `horcrux --help` works on your system run the following command

```
> pyinstaller $(which horcrux) --paths ~/.virtualenvs/temp-env/lib/python3.8/site-packages --hidden-import=_cffi_backend --onefile
```

This will package and compile all the required files and imports into a single exe at
`dist/horcrux`. Consult the [pyinstaller docs](https://pyinstaller.readthedocs.io/en/stable/) 
to adapt the pyinstaller call for windows or other environment configurations.

## Use
### Splitting


```
usage: horcrux split [-h] [-f FILENAME] INFILE [OUTPUT] THRESHOLD N

positional arguments:
  INFILE                File or stream to break into horcruxes. Supports
                        reading from stdin with "-".
  OUTPUT                Where to place created horcruxes.
  THRESHOLD             Number of horcrux files needed to re-assemble input.
  N                     Number of horcrux files to make.

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        What to title re-assembled file. Usefull when
                        processing streams.

examples:
    horcrux split passwords.txt ~/horcruxes 2 5
    horcrux split myfile.txt ~/horcruxes/my_hx 4 5
    tar c "Documents" | horcrux split - doc_horcrux --filename Documents.tar 2 2
```

### Combining
```
usage: horcrux combine [-h] [--output [OUTPUT]] [--overwrite]
                       INPUT_FILES [INPUT_FILES ...]

positional arguments:
  INPUT_FILES

optional arguments:
  -h, --help         show this help message and exit
  --output [OUTPUT]  Where to place the newly reconstructed file.
  --overwrite, -f    Overwrite files without prompting

examples:
    horcrux combine ~/horcruxes/passwords_1.hrcx ~/horcruxes/passwords_4.hrcx
    horcrux combine my_hx_* --output=reconstructed_file.txt
    horcrux combine doc_horcrux_1.hrcx doc_horcrux_2.hrcx --output - | tar x
```

### How it works

When splitting, a random 256 bit encryption key is generated and then split into n pieces.
That key is then used to encrypt the input data into blocks which are then distributed to
the horcrux files. Horcrux attempts to allocate the blocks in such a way no combination of
less than the given threshold of files has all the blocks of the original file. 

When combining, Horcrux reads the headers of the given horcruxes and ensures they have
matching ids. It then attempts to recombine the key shares into the original encryption
key. If there are enough shares, the key will be recovered correctly and the blocks will
be reassembled into the original input.


### Security

The random encryption key is split using Shamir Secret Sharing. This ensures that no part
of the key can be recovered without at least the required number of shares. That is, there
is zero information until some threshold of shared pieces are re-combined. The file is
then broken up and encrypted using libsodium.

#### SSS

Shamir Secret Sharing works by exploiting the fact that 2 points are required to describe
a line, 3 points are required to describe a parabola, and so on and so forth. By choosing
a random polynomial where order=threshold we can set our secret to be some point along
that curve (usually the y-intercept). We can then distribute other points along that curve
to our horcurxes, as many as we want, and be assured that the correct curve can only be
assembled with the threshold number of points. 

As an example, lets say we want 5 horcruxes and that at least 3 are required to recover
the encryption key. We would generate a random key, the hash of that key, and one more
completely random point. We would then construct the parabola that goes through these
three points. Then we would choose 5 new points along that curve, and place them in our
horcruxes. If any 3 horcruxes are combined, the original parabola can be reconstructed
using the x and y values they contain.  Then we use that reconstructed curve to calculate
the value at the x-positions of our random key, and the key's hash. We use the hash to
check that we have recovered the key correctly and then use the key to start decrypting
blocks from the horcruxes.

#### Encryption

The input file is broken into blocks and fed though libsodium's xChaCha20-poly1305 stream
encryption. Copies of each block are then distributed to the horcrux files in such a way
that no combination of horcruxes that is less than the required number has all the blocks
from the input file (this is not always possible when there are a large number of
horcruxes, so it does its best). The encryption cipher is re-keyed after each block, so
that even if the original encryption key is brute forced on a single horcrux, only the
first few blocks would be readable; the first missing block would cause a re-key that the
attacker couldn't replicate, meaning they'd have to brute force all over again.
