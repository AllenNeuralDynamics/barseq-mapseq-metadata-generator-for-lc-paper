"""Top-level run script.

Iterates the SUBJECTS dict, builds Procedures + MAPseq + BARseq Acquisition
objects for each, validates each via JSON round-trip, and writes the JSON
files to /results/<subject_id>/.

Output layout:
    /results/780345/procedures.json
    /results/780345/mapseq_acquisition.json
    /results/780345/barseq_acquisition.json
    /results/780346/procedures.json
    /results/780346/mapseq_acquisition.json
    /results/780346/barseq_acquisition.json
"""

import os
from pathlib import Path

from aind_data_schema.core.acquisition import Acquisition
from aind_data_schema.core.procedures import Procedures

from generators import (
    build_barseq_acquisition,
    build_mapseq_acquisition,
    build_procedures,
)
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
        out_dir = RESULTS_DIR / subject_id
        out_dir.mkdir(parents=True, exist_ok=True)

        procedures = _validate_roundtrip(build_procedures(subject_id, cfg), Procedures)
        mapseq_acq = _validate_roundtrip(build_mapseq_acquisition(subject_id, cfg, procedures), Acquisition)
        barseq_acq = _validate_roundtrip(build_barseq_acquisition(subject_id, cfg, procedures), Acquisition)

        (out_dir / "procedures.json").write_text(procedures.model_dump_json(indent=3))
        (out_dir / "mapseq_acquisition.json").write_text(mapseq_acq.model_dump_json(indent=3))
        (out_dir / "barseq_acquisition.json").write_text(barseq_acq.model_dump_json(indent=3))

        print(f"  procedures.json:           {len(procedures.specimen_procedures)} specimen procedures")
        print(f"  mapseq_acquisition.json:   {len(mapseq_acq.specimen_id)} specimens")
        print(f"  barseq_acquisition.json:   {len(barseq_acq.specimen_id)} specimens")

    print(f"\nWrote {len(SUBJECTS)} subject(s) to {RESULTS_DIR}")


if __name__ == "__main__":
    run()
