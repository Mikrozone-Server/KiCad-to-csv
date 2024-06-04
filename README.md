# KiCad to CSV library parameters exporter

Utility to export KiCad symbol's parameters from the symbol library to .csv format, even with user-defined fields.


## Prerequisites

- Python 3.7 or higher
- Python3-pip
- `requirements.txt`
  - [kiutils](https://github.com/mvnmgrx/kiutils)


## Installation

```sh
pip install -r requirements.txt
```


## Using

```sh
# display help
usage: kicad-export.py [-h] -i <file_or_dir> -o output_file

arguments:
  -h | --help                 - Show this help message and exit
  -i | --input <file_or_dir>  - Path to input directory or single file (.kicad_sym)
  -o | --output <output_file> - Output filename (.csv)


# process single file
python3 kicad-export.py -i <my-file.kicad_sym> -o my-file.csv

# process all files in directory
python3 kicad-export.py -i <path-to-kicad_sym-directory> -o my-dir.csv
```


### Example

```sh
python3 kicad-export.py -i tests/symbols -o output.csv
Start processing...
Processing done

cat output.csv
"Lib_PATH+FILENAME","SYMBOLNAME","Description","Keywords","Reference","Value","Footprint","Datasheet","Technology","MFG","MPN","Device_Marking","OC_LCSC","OC_MOUSER","OC_RS","OC_DISTRELEC","OC_TME","OC_FARNELL","OC_DIGIKEY","OC_SOS","Z-SYSCODE","Assembly_Note","Comment","ki_fp_filters"
"tests/symbols/symbol.kicad_sym","PKLCS1212E4001-R1","SMD Piezo element non polarised, 65 dB (4kHz)","BZ","RE","PKLCS1212E4001-R1","SMD_Audio_Murata:SPK_1200X1200H300-2N_PLKCS_MURATA","https://www.farnell.com/datasheets/2157985.pdf","SMD","Murata","PKLCS1212E4001-R1","","","","","","","1192551","","","1813","","","SPK_1200X1200H300-2?_PLKCS_MURATA*"
```
