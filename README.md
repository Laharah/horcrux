=======
# Horcrux
=======

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
usage: horcrux combine [-h] [--output [OUTPUT]] INPUT_FILES [INPUT_FILES ...]

positional arguments:
  INPUT_FILES

optional arguments:
  -h, --help         show this help message and exit
  --output [OUTPUT]  Where to place the newly reconstructed file.

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
is zero information until some threshold of shared pieces are re-combined. 

### SSS

Shamie Secret Sharing works by exploiting the fact that 2 points are required to describe
a line, 3 points are required to describe a parabola, and so on and so forth. By choosing
a polynomile equation  
