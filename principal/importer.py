"""Principal importer — QFX to Portfolio Performance format."""

from qfx.pipeline import QfxImporter


class PrincipalImporter(QfxImporter):
    label = "Principal"
    account_name = "Manju-Principal"


if __name__ == "__main__":
    PrincipalImporter("pr*.qfx").run("data", "output")
