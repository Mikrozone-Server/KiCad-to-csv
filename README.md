# KiCad to CSV library parameters exporter

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
usage: kicad-export.py [-h] INPUT_DIR-FILE OUTPUT_CSV_FILE

KiCad library symbol exporter (CSV)

positional arguments:
  INPUT_DIR-FILE   Path to input directory or single file (.kicad_sym)
  OUTPUT_CSV_FILE  Output filename (.csv)

optional arguments:
  -h, --help       Show this help message and exit
```


# Examples of usage

```sh
# process single file
python3 kicad-export.py <my-file.kicad_sym> my-file.csv

# process all files in directory
python3 kicad-export.py <path-to-kicad_sym-directory> my-dir.csv
```
