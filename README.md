=======
# Horcrux
=======

Split a file into n encrypted horcruxes, that can only be decrypted by re-combining k of them.


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

## Use
### Splitting


```

usage: horcrux split [-h] [-f FILENAME] N THRESHOLD INFILE [OUTPUT]

positional arguments:
  N                     Number of horcrux files to make.
  THRESHOLD             Number of horcrux files needed to re-assemble input.
  INFILE                File or stream to break into horcruxes. Supports
                        reading from stdin with "-".
  OUTPUT                Where to place created horcruxes.

optional arguments:
  -h, --help            show this help message and exit
  -f FILENAME, --filename FILENAME
                        What to title re-assembled file. Usefull when
                        processing streams.


```

### Combining
```
usage: horcrux combine [-h] [--output [OUTPUT]] INPUT_FILES [INPUT_FILES ...]

positional arguments:
  INPUT_FILES

optional arguments:
  -h, --help         show this help message and exit
  --output [OUTPUT]  Where to place the newly reconstructed file.
```
