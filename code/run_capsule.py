"""Top-level run script.

Iterates the SUBJECTS dict, builds Procedures + MAPseq + BARseq Acquisition
objects for each, validates each via JSON round-trip, and writes the JSON
files to /results/<subject_id>/<modality>/.

The same procedures.json is written into both modality folders — the brain
was sectioned once and the Procedures object is per-subject, not per-modality.
Repeating it lets each modality folder be uploaded as a self-contained unit.

Each modality folder also receives a gather_metadata_settings.json — the
JobSettings file consumed by aind-metadata-mapper's gather_metadata job to
fetch subject.json and complete data_description.json from the AIND on-prem
metadata service. See README.md for the local invocation.

Output layout (per subject):
    <subject>/mapseq/procedures.json
    <subject>/mapseq/acquisition.json
    <subject>/mapseq/gather_metadata_settings.json
    <subject>/barseq/procedures.json
    <subject>/barseq/acquisition.json
    <subject>/barseq/gather_metadata_settings.json
"""

import json
import os
from pathlib import Path

from aind_data_schema.core.acquisition import Acquisition
from aind_data_schema.core.procedures import Procedures

from acquisition_generator import build_barseq_acquisition, build_mapseq_acquisition
from gather_metadata_settings_generator import build_gather_metadata_settings
from procedures_generator import build_procedures
from subjects import SUBJECTS

# Code Ocean mounts /results/ as the canonical output location. Override
# via CO_RESULTS_DIR for local testing.
RESULTS_DIR = Path(os.environ.get("CO_RESULTS_DIR", "/results"))


def _validate_roundtrip(model_obj, model_cls):
    """Serialize and re-validate. Confirms the object is valid JSON before writing."""
    return model_cls.model_validate_json(model_obj.model_dump_json())


def run() -> None:
    for subject_id, cfg in SUBJECTS.items():
        print(f"=== {subject_id} ===")
        mapseq_dir = RESULTS_DIR / subject_id / "mapseq"
        barseq_dir = RESULTS_DIR / subject_id / "barseq"
        mapseq_dir.mkdir(parents=True, exist_ok=True)
        barseq_dir.mkdir(parents=True, exist_ok=True)

        procedures = _validate_roundtrip(build_procedures(subject_id, cfg), Procedures)
        mapseq_acq = _validate_roundtrip(build_mapseq_acquisition(subject_id, cfg, procedures), Acquisition)
        barseq_acq = _validate_roundtrip(build_barseq_acquisition(subject_id, cfg, procedures), Acquisition)

        procedures.write_standard_file(output_directory=mapseq_dir)
        procedures.write_standard_file(output_directory=barseq_dir)
        mapseq_acq.write_standard_file(output_directory=mapseq_dir)
        barseq_acq.write_standard_file(output_directory=barseq_dir)

        mapseq_settings = build_gather_metadata_settings(subject_id, "MAPseq")
        barseq_settings = build_gather_metadata_settings(subject_id, "BARseq")
        (mapseq_dir / "gather_metadata_settings.json").write_text(json.dumps(mapseq_settings, indent=3))
        (barseq_dir / "gather_metadata_settings.json").write_text(json.dumps(barseq_settings, indent=3))

        print(f"  procedures.json:           {len(procedures.specimen_procedures)} specimen procedures (written to both modality folders)")
        print(f"  mapseq/acquisition.json:   {len(mapseq_acq.specimen_id)} specimens")
        print(f"  barseq/acquisition.json:   {len(barseq_acq.specimen_id)} specimens")
        print(f"  gather_metadata_settings.json written to both modality folders")

    print(f"\nWrote {len(SUBJECTS)} subject(s) to {RESULTS_DIR}")


if __name__ == "__main__":
    run()
