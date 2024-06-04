import os, sys
import csv
import argparse
from kiutils.symbol import SymbolLib

KI_VALUES = ["ki_description", "ki_keywords"]

ALL_PROPERTIES = [
    "Reference",
    "Value",
    "Footprint",
    "Datasheet",
    "Technology",
    "MFG",
    "MPN",
    "Device_Marking",
    "OC_LCSC",
    "OC_MOUSER",
    "OC_RS",
    "OC_DISTRELEC",
    "OC_TME",
    "OC_FARNELL",
    "OC_DIGIKEY",
    "OC_SOS",
    "Z-SYSCODE",
    "Assembly_Note",
    "Comment",
    "ki_fp_filters",
]

CSV_HEADER = [
    "Lib_PATH+FILENAME",
    "SYMBOLNAME",
    "Description",
    "Keywords",
] + ALL_PROPERTIES


if __name__ == "__main__":
    # process arguments
    parser = argparse.ArgumentParser(
        description="KiCad library symbol exporter (CSV)", add_help=False
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    parser.add_argument(
        "input_dirfile",
        help="Path to input directory or single file (.kicad_sym)",
    )
    parser.add_argument(
        "output_file",
        help="Output filename (.csv)",
    )

    args = parser.parse_args()

    # check if input is file or dir
    input_files = []
    if os.path.exists(args.input_dirfile):
        if os.path.isfile(args.input_dirfile):
            input_files.append(args.input_dirfile)
        else:
            input_files = [
                os.path.abspath(os.path.join(args.input_dirfile, f))
                for f in os.listdir(args.input_dirfile)
                if f.endswith(".kicad_sym")
            ]
    else:
        print(args.input_dirfile + " does not exists!")
        sys.exit(1)

    print("Start processing...")

    # write csv file
    with open(args.output_file, "w", newline="") as csv_file:
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

        # write csv header
        writer.writerow(CSV_HEADER)

        # loop over input file/s
        for f in input_files:
            try:
                symbol_lib = SymbolLib().from_file(f)

                # loop over all symbols
                for s in symbol_lib.symbols:
                    # print path and name
                    row = [symbol_lib.filePath, s.entryName]

                    # convert properties list to dictionary for quicker access
                    props_dict = {prop.key: prop for prop in s.properties}

                    # print ki_ values
                    for k in KI_VALUES:
                        row.append(props_dict.get(k).value if k in props_dict else "")

                    # print rest of properties
                    for k, p in props_dict.items():
                        if k in ALL_PROPERTIES:
                            row.append(p.value)
                        elif k not in KI_VALUES:
                            row.append("")
                            print(
                                f'{os.path.basename(symbol_lib.filePath)}:{s.entryName}: "{k}" is missing'
                            )

                    # write row to csv
                    writer.writerow(row)
            except Exception as ex:
                print(f'"Unable to process {f}", err: {ex}')

    print("Processing done")
