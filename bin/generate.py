"""
Usage:
  generate.py --files=file1,file2 --check
  generate.py --files=file1,file2 --urlcheck [--url=<URL>]
  generate.py --files=file1,file2 --format=<fmt> --outdir=<dir> [--authortruncation=N] [--columns=col1,col2] [--check] [--noratings] [--required] [--standalone] [--withcitation] [--urlcheck]
  generate.py --check_log


Options:
  --files=<file>...           YAML file paths to process (one or more) [default: source/benchmark-addon.yaml].
  --format=<fmt>              Output file format [default: tex].
  --outdir=<dir>              Output directory [default: ./content/].
  --authortruncation=N        Truncate authors for index pages [default: 9999].
  --columns=<cols>            Subset of columns to include, comma-separated.
  --check                     Conduct formatting checks only.
  --noratings                 Removes rating columns from output.
  --required                  Requires all specified columns to exist.
  --standalone                Include full LaTeX document preamble (tex only).
  --withcitation              Add a citation row (md only).
  --urlcheck                  Check if URLs exist.
  --check_log                 Check the latex log file by removing unneded content
  --url=<URL>                 URL to check for validity (used with --urlcheck).

Notes:
  - --standalone is only valid with --format=tex
  - --withcitation is only valid with --format=md
  - Author truncation must be a positive integer
"""
import os
import sys
import logging
from docopt import docopt
from typing import Union, Dict
from yaml_manager import YamlManager
from md_writer import MarkdownWriter
from generate_latex import GenerateLatex, ALL_COLUMNS
from check_log import print_latex_log
from yaml_manager import find_unicode_chars

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

VERBOSE = True
if VERBOSE:
    logger.info("Starting the generation process...")

if __name__ == "__main__":
    args = docopt(__doc__)

    check_log = args["--check_log"]
    if check_log:
        print_latex_log(filename="content/tex/benchmarks.log")
        sys.exit(0)

    format_type = args["--format"] or "tex"
    output_dir = args["--outdir"] or "./content/"

    author_trunc = int(args["--authortruncation"])

    files = args["--files"]
    if files is None:
        files = ["source/benchmark-addon.yaml"]
    else:
        files = files.split(",")

    columns = args["--columns"]
    if columns is None:
        columns = ALL_COLUMNS.keys()
    else:
        columns = columns.split(",")

    if args["--standalone"] and format_type != "tex":
        logger.error("--standalone is only valid with --format=tex")
        sys.exit(1)

    if args["--withcitation"] and format_type != "md":
        logger.error("--withcitation is only valid with --format=md")
        sys.exit(1)

    if author_trunc <= 0:
        logger.error("--authortruncation must be a positive integer")
        sys.exit(1)

    for file in files:
        if not os.path.exists(file):
            logger.error(f"File not found: {file}")
            sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    manager = YamlManager(files)
    entries = manager.get_flat_dicts()

    if args["--check"]:

        for file in files:
            if not os.path.exists(file):
                logger.error(f"File not found: {file}")
                sys.exit(1)
            logger.info("Checking YAML files for formatting issues...")
            find_unicode_chars(filename=file)

        manager.check_required_fields()
        sys.exit(0)

    if args["--required"]:
        if not manager.check_required_fields():
            sys.exit(0)

    if args["--urlcheck"]:

        if args["--url"]:
            url = args["--url"]
            if not manager.is_url_valid(url):
                logger.error(f"URL {url} is not valid.")
                sys.exit(1)
            logger.info(f"URL {url} is valid.")
            sys.exit(0)
        else:
            logger.info("Checking URLs ...")
            manager.check_urls()
            sys.exit(0)

    if format_type == "md":

        converter = MarkdownWriter(entries, raw_entries=manager.data)
        converter.write_table(columns=columns)
        converter.write_individual_entries(columns=columns)

    elif format_type == "tex":
        converter = GenerateLatex(entries)

        converter.generate_radar_chart_grid()

        logger.info("Generating radar charts...")
        converter.generate_radar_charts(fmt="pdf")
        converter.generate_radar_charts(fmt="png")

        logger.info("Generating LaTeX table...")
        converter.generate_table()
        logger.info("Generating LaTeX BibTeX...")
        converter.generate_bibtex()
        logger.info("Generating section document...")
        converter.generate_section()
        logger.info("Generating document...")
        converter.generate_document()