import os, sys
import csv
import argparse
import logging
import re
from kiutils.footprint import Footprint, Model
from kiutils.symbol import SymbolLib

### VERSION
__version_info__ = ("0", "2", "0")
__version__ = ".".join(__version_info__)

# configure global logger
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger("global_logger")


class CSVHandler:
    def __init__(self, path: str, writer: bool):
        self.path = path
        self._file = None
        self._csv = None
        self._init(writer)

    def __del__(self):
        if self._file:
            self._file.close()

    def _init(self, writer: bool):
        try:
            if writer:
                self._file = open(self.path, "w", newline="")
                self._csv = csv.writer(self._file, quoting=csv.QUOTE_ALL)
            else:
                self._file = open(self.path, "r")
                self._csv = csv.reader(self._file)
        except IOError as ex:
            LOGGER.error(f'"Unable to process {f}", err: {ex}')
            self._csv = None
            self._file = None
            raise ex

    def write(self, row: list):
        self._csv.writerow(row)

    def read(self) -> list:
        return next(self._csv, None)

    def read_all(self):
        for row in self._csv:
            yield row


class Footprints(Footprint):
    def __init__(self, files: str or list = []):
        self.files = files
        self.ATTRIBUTES = {
            "root": [
                "description",
                "models",
            ],
            "attributes": [
                "allowMissingCourtyard",
                "boardOnly",
                "excludeFromBom",
                "excludeFromPosFiles",
                "type",
            ],
        }
        self.PROPERTIES = []
        super().__init__()

    def _convert_number(self, number: str) -> float or int:
        return float(number) if "." in number else int(number)

    def create_model(self, smodel: str) -> list:
        model = ["model"]

        # regex pattern to match key-value pairs
        pattern = re.compile(r"(\w+)=('.*?'|Coordinate\(.*?\)|\w+|\w+\(.*?\))")

        # find all key-value pairs
        matches = pattern.findall(smodel.strip()[6:-1])

        for key, value in matches:
            if key == "path":
                model.append(value.strip("'"))
            elif key == "hide" and value == "True":
                model.append("hide")
            elif value.startswith("Coordinate"):
                # extract the values inside Coordinate()
                coords = re.findall(r"-?\d+(?:\.\d+)?", value)
                # pos is save as offset
                model.append(
                    [
                        key if key != "pos" else "offset",
                        ["xyz"] + [self._convert_number(coord) for coord in coords],
                    ]
                )
            elif value.startswith("'") and value.endswith("'"):
                # path
                model.append(value.strip("'"))
            elif value == "None":
                model.append([key, None])
            else:
                model.append([key, value])

        return Model().from_sexpr(model)

    def load(self, path: str):
        self.__dict__.update(self.from_file(path).__dict__)

    def items(self, path: str = "") -> list:
        return [self] if not path else [self.from_file(path)]


class Symbols(SymbolLib):
    def __init__(self, files: str or list = []):
        self.files = files
        self.ATTRIBUTES = {"root": [], "attributes": []}
        self.PROPERTIES = [
            "ki_description",
            "ki_keywords",
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
        super().__init__()

    def items(self, path: str = "") -> list:
        return self.symbols if not path else self.from_file(path).symbols

    def load(self, path: str):
        self.__dict__.update(self.from_file(path).__dict__)


class Components:
    def __init__(self, sim_or_foot: object, csv_file: str, export: bool):
        self._COMMON_PROPERTIES = ["Lib_PATH+FILENAME", "COMPONENT"]
        self._sim_or_foot = sim_or_foot
        self._csv_handler = None
        self._init(csv_file, export)

    def _init(self, csv_file: str, export: bool):
        try:
            self._csv_handler = CSVHandler(csv_file, export)
        except IOError as ex:
            LOGGER.error(f'"Unable to process {f}", err: {ex}')

    def _get_keys(self, path: str, name: str, keys: list, items: dict) -> list:
        row = []
        # loop over keys
        for key in keys:
            item = items.get(key, "")
            row.append(item)
            LOGGER.debug(f'   "{key}": "{item}"')

        # print missing entries
        for entry in set(keys).symmetric_difference(items.keys()):
            LOGGER.warning(f'{os.path.basename(path)}:{name}: "{entry}" is missing')
        return row

    def export(self):
        # write csv header
        self._csv_handler.write(
            self._COMMON_PROPERTIES
            + self._sim_or_foot.ATTRIBUTES["root"]
            + self._sim_or_foot.ATTRIBUTES["attributes"]
            + self._sim_or_foot.PROPERTIES
        )

        LOGGER.debug("[")

        # create objects based on files
        for f in self._sim_or_foot.files:
            try:
                LOGGER.debug(f" {f} = [")
                # loop over items
                for i in self._sim_or_foot.items(f):
                    LOGGER.debug(f"  {i.entryName} = {{")
                    # set path and name for COMMON_PROPERTIES
                    row = [f, i.entryName]

                    # write atrributes and properties
                    for e, v in [
                        (
                            self._sim_or_foot.ATTRIBUTES["root"],
                            {
                                a: getattr(i, a, "")
                                for a in self._sim_or_foot.ATTRIBUTES["root"]
                            },
                        ),
                        (
                            self._sim_or_foot.ATTRIBUTES["attributes"],
                            i.attributes.__dict__ if hasattr(i, "attributes") else {},
                        ),
                        (
                            self._sim_or_foot.PROPERTIES,
                            (
                                i.properties
                                if isinstance(i.properties, dict)
                                else {prop.key: prop.value for prop in i.properties}
                            ),
                        ),
                    ]:
                        row += self._get_keys(f, i.entryName, e, v)

                    # write row
                    self._csv_handler.write(row)

                    LOGGER.debug("  },")
                LOGGER.debug(" ],")

            except Exception as ex:
                LOGGER.error(f'"Unable to process {f}", err: {ex}')

            LOGGER.debug("]")

    def update(self):
        # read header
        properties = self._csv_handler.read()
        # read first entry do to header verification
        first_component = self._csv_handler.read()
        self._sim_or_foot = (
            Symbols() if first_component[0].endswith(".kicad_sym") else Footprints()
        )
        # check if properties are matching
        for p in properties:
            if (
                p
                not in self._COMMON_PROPERTIES
                + self._sim_or_foot.ATTRIBUTES["root"]
                + self._sim_or_foot.ATTRIBUTES["attributes"]
                + self._sim_or_foot.PROPERTIES
            ):
                LOGGER.warning(f'Property "{p}" is missing')
                # remove property from list
                properties.remove(p)

        LOGGER.debug("[")

        # loop over entries
        for l in [first_component] + list(self._csv_handler.read_all()):
            # skip non existing files
            if not os.path.exists(l[0]):
                LOGGER.warning(l[0] + " does not exist, skipping...")
                continue

            try:
                LOGGER.debug(f" {os.path.dirname(l[0])} = [")

                # create symbols or footprints based on first component
                self._sim_or_foot.load(l[0])
                for i in self._sim_or_foot.items():
                    # update required component only
                    if l[1] != i.entryName:
                        continue

                    LOGGER.debug(f"  {l[1]} = {{")

                    # create properties dictionary for quicker access
                    props = {prop.key: prop for prop in i.properties}

                    # update properties one by one
                    for idx, p in enumerate(properties[2:], 2):
                        # use update function based on property type
                        if p in self._sim_or_foot.ATTRIBUTES["root"]:
                            (
                                setattr(i, p, l[idx])
                                if p != "models"
                                else setattr(
                                    i,
                                    p,
                                    [self._sim_or_foot.create_model(l[idx])],
                                )
                            )
                        elif p in self._sim_or_foot.ATTRIBUTES["attributes"]:
                            setattr(i, p, l[idx])
                        else:
                            props[p].value = l[idx]
                        LOGGER.debug(f'   "{p}": "{l[idx]}"')

                    LOGGER.debug("  },")

                # save changes
                self._sim_or_foot.to_file(l[0])

                LOGGER.debug(" ],")
            except Exception as ex:
                LOGGER.error(f'"Unable to process {l[0]}", err: {ex}')

        LOGGER.debug("]")


if __name__ == "__main__":
    # process arguments
    parser = argparse.ArgumentParser(
        description="KiCad to CSV library's parameters exporter", add_help=False
    )
    parser.add_argument(
        "-h", "--help", action="help", help="Show this help message and exit"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Display debug output"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s " + __version__,
        help="Show program's version number and exit",
    )
    parser.add_argument(
        "-a",
        "--action",
        dest="action_type",
        action="store",
        choices=["import", "export"],
        help="Action to be used for processing (import|export)",
        required=True,
    )
    parser.add_argument(
        "kicad_dirfile",
        help="Path to directory or single file (.kicad_sym|.pretty)",
    )
    parser.add_argument(
        "csv_dirfile",
        help="Path to directory or single file (.csv)",
    )

    args = parser.parse_args()

    # set logging level
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)

    # convert action type to bool
    action_type_export = args.action_type == "export"
    # set input file based on action
    input_file = args.kicad_dirfile if action_type_export else args.csv_dirfile

    # set the default to import
    sym_or_foot = None

    # check if input exists
    kicad_dirfile = []
    if os.path.exists(input_file):
        # check if kicad_dirfile is file
        if os.path.isfile(args.kicad_dirfile):
            kicad_dirfile.append(args.kicad_dirfile)
        else:
            # search for .kicad_sym files without recursion
            kicad_dirfile.extend(
                os.path.join(args.kicad_dirfile, f)
                for f in os.listdir(args.kicad_dirfile)
                if f.endswith(".kicad_sym")
            )

            # search for .kicad_mod files in .pretty directories recursively
            if not kicad_dirfile:
                for root, dirs, files in os.walk(args.kicad_dirfile):
                    if root.endswith(".pretty"):
                        kicad_dirfile.extend(
                            os.path.join(root, f)
                            for f in files
                            if f.endswith(".kicad_mod")
                        )

        if action_type_export:
            if kicad_dirfile:
                # create object based on kicad type
                sym_or_foot = (
                    Symbols(kicad_dirfile)
                    if kicad_dirfile[0].endswith(".kicad_sym")
                    else Footprints(kicad_dirfile)
                )
            else:
                LOGGER.error(
                    f'"{input_file}" is not pointing to valid ".kicad_sym" or ".kicad_mod" file!'
                )
                sys.exit(1)
        else:
            if os.path.getsize(input_file) <= 0:
                LOGGER.error(input_file + " is empty!")
                sys.exit(1)
    else:
        LOGGER.error(input_file + " does not exists!")
        sys.exit(1)

    # create component based on action
    comp = Components(sym_or_foot, args.csv_dirfile, action_type_export)

    LOGGER.info("Processing...")

    # process action
    comp.export() if action_type_export else comp.update()

    LOGGER.info("Done")
