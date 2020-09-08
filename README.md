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
