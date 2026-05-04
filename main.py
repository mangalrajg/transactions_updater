"""
Main orchestrator — runs all importers in sequence.
  Source files : data/
  Output files : output/  (wiped and recreated on each run)

To add a new importer: implement BaseImporter, then add one line to IMPORTERS.
To change a file pattern: edit it here in IMPORTERS — one place for all patterns.
"""

import os
import shutil
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bofa.csv_importer import BofaImporter
from chase.csv_importer import ChaseImporter
from fidelity.csv_importer import FidelityImporter
from empower.importer import EmpowerImporter
from principal.importer import PrincipalImporter
from importer_base import BaseImporter

DATA_FOLDER = "data"
OUTPUT_FOLDER = "output"

# All file patterns live here — one place to change them.
IMPORTERS: list[BaseImporter] = [
    BofaImporter("bo*.csv"),
    ChaseImporter("ch*.csv"),
    FidelityImporter("fi*.csv"),
    EmpowerImporter("Em*.qfx"),
    PrincipalImporter("pr*.qfx"),
]


def main():
    print("=" * 60)
    print("Starting transaction imports")
    print(f"  source : {DATA_FOLDER}/")
    print(f"  output : {OUTPUT_FOLDER}/")
    print("=" * 60)

    # Wipe and recreate the output folder for a clean run
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER)

    for importer in IMPORTERS:
        print(f"\n>>> Running {importer.label} importer...")
        try:
            importer.run(DATA_FOLDER, OUTPUT_FOLDER)
            print(f"✓ {importer.label} completed")
        except Exception as e:
            print(f"✗ {importer.label} failed: {e}")
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"All imports done. Output files are in '{OUTPUT_FOLDER}/'")
    print("=" * 60)


if __name__ == "__main__":
    main()
