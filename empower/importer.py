"""Empower importer — QFX to Portfolio Performance format."""

from qfx.pipeline import QfxImporter


class EmpowerImporter(QfxImporter):
    label = "Empower"
    account_name = "Mangal-Empower"


if __name__ == "__main__":
    EmpowerImporter("Em*.qfx").run("../data", "output")
