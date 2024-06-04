# KiCad to CSV library's parameters exporter (0.0.1)

Utility to export KiCad symbol's parameters from the symbol library to `.csv` format, even with user-defined fields.
![logo](docs/logo.png)


## Prerequisites

- Python 3.7 or higher
- Python3-pip
- `requirements.txt`
  - [kiutils](https://github.com/mvnmgrx/kiutils)


## Installation

```sh
pip install -r requirements.txt
```


## Display help

```
$ python3 kicad-export.py --help
usage: kicad-export.py [-h] [-v] input_dirfile output_file

KiCad to CSV library's parameters exporter

positional arguments:
  input_dirfile  Path to input directory or single file (.kicad_sym)
  output_file    Output filename (.csv)

optional arguments:
  -h, --help     Show this help message and exit
  -v, --version  Show program's version number and exit
```


# Examples of usage

```sh
# process single file
python3 kicad-export.py <my-file.kicad_sym> my-file.csv

# process all files in directory
python3 kicad-export.py <path-to-kicad_sym-directory> my-dir.csv
```
