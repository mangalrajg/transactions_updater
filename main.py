"""
Main orchestrator to run all importers one by one.
Importers read files from the 'data' folder and write outputs to 'output' folder.
"""

import os
import shutil
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bofa.csv_importer import import_all_bofa
from chase.csv_importer import import_all_chase
from fidelity.csv_importer import import_all_fidelity
from empower.importer import import_empower
from principal.importer import import_principal


def main():
    """Run all importers in sequence"""
    data_folder = "data"
    output_folder = "output"

    print("=" * 60)
    print("Starting transaction imports from data folder...")
    print("=" * 60)
    print()

    # Clean up old output folder
    if os.path.exists(output_folder):
        print(f"Cleaning up old {output_folder} folder...")
        shutil.rmtree(output_folder)

    # Create fresh output folder
    os.makedirs(output_folder, exist_ok=True)
    print(f"Created {output_folder} folder")
    print()

    # Run importers one by one
    importers = [
        ("BofA", import_all_bofa),
        ("Chase", import_all_chase),
        ("Fidelity", import_all_fidelity),
        ("Empower", import_empower),
        ("Principal", import_principal),
    ]

    for name, importer_func in importers:
        try:
            print(f"\n>>> Running {name} importer...")
            importer_func(data_folder, output_folder)
            print(f"✓ {name} import completed successfully")
        except Exception as e:
            print(f"✗ Error during {name} import: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print("All imports completed!")
    print(f"Output files are in the '{output_folder}' folder")
    print("=" * 60)


if __name__ == "__main__":
    main()
