"""Code Ocean entry point: build all four metadata bundles into /results/ in one pass.

No parameters. One Reproducible Run writes one folder per (subject × modality)
under /results/, named by that bundle's data_description `name`
(e.g. /results/780345_2025-03-24_12-00-00/). Each folder is a complete asset:
procedures.json, acquisition.json, subject.json, data_description.json,
processing.json, and a copy of the raw <Modality>/ folder from the attached
input asset. Save each folder out as its own data asset under that name.
"""

import os
import shutil
from pathlib import Path

from aind_data_schema.core.data_description import DataDescription
from aind_data_schema.core.procedures import Procedures
from aind_data_schema.core.subject import Subject

from acquisition_generator import build_acquisition
from procedures_generator import build_procedures
from provenance import write_processing
from subjects import SUBJECTS

MODALITIES = ("MAPseq", "BARseq")

# Code Ocean mounts these; override via env vars for local runs.
RESULTS_DIR = Path(os.environ.get("CO_RESULTS_DIR", "/results"))
DATA_DIR = Path(os.environ.get("CO_DATA_DIR", "/data"))
INPUTS_DIR = Path(__file__).parent / "inputs"


def write_bundle(subject_id: str, modality: str) -> None:
    """Build one (subject, modality) bundle into /results/<data_description name>/."""
    cfg = SUBJECTS[subject_id]
    inputs = INPUTS_DIR / subject_id

    # subject.json, the brain injections (subject_procedures), and
    # data_description come from the metadata service, prefetched into inputs/.
    subject = Subject.model_validate_json((inputs / "subject.json").read_text())
    dd = DataDescription.model_validate_json((inputs / modality.lower() / "data_description.json").read_text())
    injections = Procedures.model_validate_json(
        (inputs / "procedures_from_service.json").read_text()
    ).subject_procedures

    # Sectioning is built locally and merged with the service injections.
    # model_copy skips validation, so re-validate the merged Procedures.
    merged = build_procedures(subject_id, cfg).model_copy(update={"subject_procedures": injections})
    procedures = Procedures.model_validate_json(merged.model_dump_json())
    acquisition = build_acquisition(subject_id, cfg, procedures, modality)

    out_dir = RESULTS_DIR / dd.name
    out_dir.mkdir(parents=True, exist_ok=True)
    for obj in (subject, procedures, acquisition, dd):
        obj.write_standard_file(output_directory=out_dir)
    write_processing(out_dir)
    _copy_raw_data(subject_id, modality, out_dir)
    print(f"  {dd.name}/  ({modality})")


def _copy_raw_data(subject_id: str, modality: str, out_dir: Path) -> None:
    """Copy the modality's raw-data folder from the attached input asset into out_dir.

    Code Ocean mounts each input asset at /data/<asset>/; we match /data/<subject>_*.
    No-op (with a warning) when nothing is mounted, e.g. a local run.
    """
    matches = sorted(DATA_DIR.glob(f"{subject_id}_*"))
    if not matches:
        print(f"    WARNING: no input asset matching {subject_id}_* in {DATA_DIR}; skipping raw-data copy (expected locally).")
        return
    if len(matches) > 1:
        raise RuntimeError(f"Multiple input assets match {subject_id}_* in {DATA_DIR}: {matches}")
    src = matches[0] / modality
    if not src.is_dir():
        raise RuntimeError(f"Modality folder {src} not found in input asset")
    shutil.copytree(src, out_dir / modality)


def main() -> None:
    """Write every (subject × modality) bundle under RESULTS_DIR, one named folder each."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing bundles to {RESULTS_DIR}")
    for subject_id in SUBJECTS:
        for modality in MODALITIES:
            write_bundle(subject_id, modality)


if __name__ == "__main__":
    main()
