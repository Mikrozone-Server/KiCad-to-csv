from kiutils.symbol import SymbolLib
import sys, csv

KI_VALUES = [
    "ki_description",
    "ki_keywords"
]

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
    "ki_fp_filters"
]

CSV_HEADER = [
    "Lib_PATH+FILENAME",
    "SYMBOLNAME",
    "Description",
    "Keywords"
] + ALL_PROPERTIES


if __name__ == "__main__":
    symbol_lib = SymbolLib().from_file("tests/symbols/input.kicad_sym")
    if symbol_lib == None:
        sys.exit(1)

    # write csv file
    with open('output.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)

        # write csv header
        writer.writerow(CSV_HEADER)

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
                    print(f'"{s.entryName}": "{k}" is missing')

            # write row to csv
            writer.writerow(row)
