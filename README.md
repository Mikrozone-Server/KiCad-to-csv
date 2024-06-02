# KiCad to CSV library exporter

Utility to export KiCad symbol libraries into CSV.


## Prerequisites

- Python 3.7 or higher
- Python3-pip
- `requirements.txt`
  - [kiutils](https://github.com/mvnmgrx/kiutils)


## Installation

```sh
pip3 install -r requirements.txt
```


## Using

```sh
# display help
usage: kicad-export.py [-h] -i <file_or_dir> -o output_file

arguments:
  -h | --help                 - Show this help message and exit
  -i | --input <file_or_dir>  - Path to input directory or single file (.kicad_sym)
  -o | --output <output_file> - Output filename (.csv)


# process signle file
python3 kicad-export.py -i <my-file.kicad_sym> -o my-file.csv

# process all files in directory
python3 kicad-export.py -i <path-to-kicad_sym-directory> -o my-dir.csv
```
