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
import time
from pathlib import Path

from aind_data_schema.core.data_description import DataDescription
from aind_data_schema.core.procedures import Procedures
from aind_data_schema.core.subject import Subject

from acquisition_generator import build_acquisition
from procedures_generator import build_procedures
from provenance import write_processing
from subjects import SUBJECTS

MODALITIES = ("MAPseq", "BARseq")

# Per-subject files that belong in the raw asset but currently live in separate
# "loose CSV" assets, keyed by the modality folder they get folded into. They
# were dropped when the raw assets were rebuilt, which breaks the downstream
# matching pipeline (the analysis capsule reads them from <asset>/<Modality>/).
# Attach these in Code Ocean under exactly these mount names; files are routed
# to each subject by <subject_id> in the filename. See the README.
SUPPLEMENTAL_ASSETS = {
    "BARseq": "BARseq_soma_barcodes",
    "MAPseq": "MAPseq_ROI_info",
}

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
    _copy_supplemental_files(subject_id, modality, out_dir)
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
    print(f"    copying raw {modality}/ from '{matches[0].name}' "
          f"(largest step — copies the whole raw-data folder)…", flush=True)
    t = time.perf_counter()
    shutil.copytree(src, out_dir / modality)
    print(f"    copied raw {modality}/ in {time.perf_counter() - t:.1f}s", flush=True)


def _copy_supplemental_files(subject_id: str, modality: str, out_dir: Path) -> None:
    """Fold this subject's supplemental files into out_dir/<modality>/.

    Some per-subject files — BARseq soma-barcode QC (barcodes_BC_qc_<id>.csv,
    LC_visualQC_barcoded_cells_<id>.csv) and MAPseq ROI info — belong in the raw
    asset but currently live in separate loose-file assets (see SUPPLEMENTAL_ASSETS).
    Folding them back into each subject's <Modality>/ folder lets them flow through
    the conversion + analysis capsules, which read them from <asset>/<Modality>/.

    Files are routed to the right subject by <subject_id> in the filename. No-op
    (with a warning) if the supplemental asset isn't mounted, so runs without it
    still succeed.
    """
    asset = SUPPLEMENTAL_ASSETS.get(modality)
    if asset is None:
        return
    src_root = DATA_DIR / asset
    if not src_root.is_dir():
        print(f"    WARNING: supplemental asset '{asset}' not mounted at {src_root}; "
              f"skipping supplemental files for {subject_id} {modality}.")
        return
    dest = out_dir / modality
    dest.mkdir(parents=True, exist_ok=True)
    copied = [p for p in sorted(src_root.rglob(f"*{subject_id}*")) if p.is_file()]
    for path in copied:
        shutil.copy2(path, dest / path.name)
    if copied:
        names = ", ".join(p.name for p in copied)
        print(f"    supplemental ('{asset}'): copied {len(copied)} file(s) into {modality}/: {names}")
    else:
        print(f"    WARNING: no files matching *{subject_id}* in '{asset}'; nothing copied.")


def main() -> None:
    """Write every (subject × modality) bundle under RESULTS_DIR, one named folder each."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pairs = [(subject_id, modality) for subject_id in SUBJECTS for modality in MODALITIES]
    total = len(pairs)
    print(f"Writing {total} bundles to {RESULTS_DIR}", flush=True)
    run_start = time.perf_counter()
    for i, (subject_id, modality) in enumerate(pairs, start=1):
        print(f"[{i}/{total}] {subject_id} {modality}: building bundle…", flush=True)
        started = time.perf_counter()
        write_bundle(subject_id, modality)
        print(f"[{i}/{total}] {subject_id} {modality}: done in {time.perf_counter() - started:.1f}s", flush=True)
    print(f"All {total} bundles written to {RESULTS_DIR} in {time.perf_counter() - run_start:.1f}s.", flush=True)


if __name__ == "__main__":
    main()
