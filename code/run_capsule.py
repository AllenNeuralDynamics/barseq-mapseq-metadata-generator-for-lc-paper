"""Top-level run script.

Builds the metadata bundle for one (subject, modality) and writes it to
/results/, alongside a copy of the raw modality folder pulled from the
attached input data asset. Each Reproducible Run on Code Ocean produces
one /results/ folder, which becomes one data asset; the four (subject,
modality) combos require four runs.

Parameters (passed from the Code Ocean App Panel as CLI args):
    --subject-id   one of the keys in SUBJECTS (e.g. "780345")
    --modality     "MAPseq" or "BARseq"

Output layout (/results/):
    procedures.json          locally-built sectioning + service injections
    acquisition.json         modality-specific
    subject.json             passthrough from the metadata service (via inputs/)
    data_description.json    modality-specific, prebuilt by prefetch_inputs.py
    <Modality>/              raw data, copied verbatim from the input asset

The fresh data_description.json's `name` field is the canonical AIND data
asset name (e.g. `mapseq_780345_2025-03-24_12-00-00`). Code Ocean should
use that when promoting /results/ to a data asset.
"""

import argparse
import os
import shutil
from pathlib import Path

from aind_data_schema.core.acquisition import Acquisition
from aind_data_schema.core.data_description import DataDescription
from aind_data_schema.core.procedures import Procedures
from aind_data_schema.core.subject import Subject

from acquisition_generator import build_acquisition
from procedures_generator import build_procedures
from provenance import augment_notes
from subjects import SUBJECTS

# Code Ocean mounts /results/ as the canonical output location. Override
# via CO_RESULTS_DIR for local testing.
RESULTS_DIR = Path(os.environ.get("CO_RESULTS_DIR", "/results"))

# Code Ocean mounts attached input data assets under /data/. Override via
# CO_DATA_DIR for local testing if you've staged data somewhere else.
DATA_DIR = Path(os.environ.get("CO_DATA_DIR", "/data"))

# Prefetched metadata committed to the repo. See prefetch_inputs.py.
INPUTS_DIR = Path(__file__).parent / "inputs"


def _validate_roundtrip(model_obj, model_cls):
    """Serialize a pydantic model to JSON and re-parse it as the same class.

    Catches a class of bug that plain serialization misses: fields that
    serialize fine but fail on re-validation (e.g. enum/string mismatches).

    Args:
        model_obj: A pydantic model instance.
        model_cls: The class to re-validate against (typically `type(model_obj)`).

    Returns:
        A freshly-parsed instance of `model_cls` whose contents equal `model_obj`.
        Raises `pydantic.ValidationError` if re-parsing fails.
    """
    return model_cls.model_validate_json(model_obj.model_dump_json())


def _load_inputs(subject_id: str, modality: str):
    """Load the prefetched inputs needed for one (subject, modality).

    Args:
        subject_id: Subject ID (e.g. "780345").
        modality: "MAPseq" or "BARseq".

    Returns:
        Tuple of (Subject, Procedures, DataDescription). The Procedures
        returned here is the *service* version — it carries the injections
        we need to merge into the locally-built procedures.
    """
    subj_dir = INPUTS_DIR / subject_id
    subject = Subject.model_validate_json((subj_dir / "subject.json").read_text())
    service_proc = Procedures.model_validate_json((subj_dir / "procedures_from_service.json").read_text())
    dd = DataDescription.model_validate_json((subj_dir / modality.lower() / "data_description.json").read_text())
    return subject, service_proc, dd


def _find_input_asset(subject_id: str) -> Path | None:
    """Find the attached input data asset for one subject.

    Code Ocean mounts each attached data asset as `/data/<asset_name>/`. We
    glob `/data/<subject_id>_*` to find the one matching this subject (the
    timestamp suffix varies between assets).

    Args:
        subject_id: Subject ID (e.g. "780345").

    Returns:
        The matching `/data/<asset>/` path, or None if no asset is attached
        (e.g. when running locally without /data/ mounted).

    Raises:
        RuntimeError: if more than one asset matches.
    """
    matches = sorted(DATA_DIR.glob(f"{subject_id}_*"))
    if not matches:
        return None
    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple input assets matching {subject_id}_* in {DATA_DIR}: {matches}. "
            f"Expected exactly one."
        )
    return matches[0]


def _copy_modality_data(asset_path: Path, modality: str, results_dir: Path) -> None:
    """Copy the chosen modality's raw-data folder from the input asset into /results/.

    Args:
        asset_path: Root of the attached input asset (e.g. `/data/780345_2025-02-20_00-00-00`).
        modality: "MAPseq" or "BARseq" — must match a subdirectory of `asset_path`.
        results_dir: Destination root (typically /results/). The modality folder
            is copied as `<results_dir>/<modality>/`.

    Raises:
        RuntimeError: if the modality subfolder doesn't exist in the input asset.
    """
    src = asset_path / modality
    if not src.is_dir():
        raise RuntimeError(f"Modality folder {src} does not exist in input asset")
    dst = results_dir / modality
    print(f"  copying {src} -> {dst} ...")
    shutil.copytree(src, dst)


def _parse_args() -> argparse.Namespace:
    """Parse args wired to Code Ocean parameters.

    Accepts either CLI flags (`--subject-id`, `--modality`) or environment
    variables (`SUBJECT_ID`, `MODALITY`), so the capsule works whether Code
    Ocean's App Panel passes parameters as args or as env vars.

    Returns:
        argparse.Namespace with `subject_id` and `modality` attributes.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--subject-id",
        default=os.environ.get("SUBJECT_ID"),
        choices=sorted(SUBJECTS.keys()),
        help="Subject ID. Defaults to the SUBJECT_ID env var.",
    )
    parser.add_argument(
        "--modality",
        default=os.environ.get("MODALITY"),
        choices=["MAPseq", "BARseq"],
        help="Modality. Defaults to the MODALITY env var.",
    )
    args = parser.parse_args()
    if not args.subject_id or not args.modality:
        parser.error(
            "Both subject-id and modality are required. Pass them as "
            "--subject-id / --modality CLI flags, or set the SUBJECT_ID / "
            "MODALITY environment variables (Code Ocean's Reproducible Run "
            "dialog has an env vars section)."
        )
    return args


def run(subject_id: str, modality: str) -> None:
    """Build and write the metadata bundle for one (subject, modality).

    Args:
        subject_id: Subject ID (must be a key in `SUBJECTS`).
        modality: "MAPseq" or "BARseq".

    Reads `CO_RESULTS_DIR` and `CO_DATA_DIR` from the environment to override
    the default `/results` and `/data` paths. Has no return value; results
    are observed via files written under `RESULTS_DIR` and a summary printed
    to stdout.
    """
    cfg = SUBJECTS[subject_id]
    print(f"=== {subject_id} {modality} ===")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    subject, service_proc, dd = _load_inputs(subject_id, modality)

    local_proc = build_procedures(subject_id, cfg)
    merged_proc = local_proc.model_copy(
        update={"subject_procedures": service_proc.subject_procedures}
    )

    procedures = _validate_roundtrip(merged_proc, Procedures)
    acquisition = _validate_roundtrip(
        build_acquisition(subject_id, cfg, procedures, modality), Acquisition
    )

    # Stamp the provenance URL onto every artifact this capsule generates
    # or assembles. subject.json is intentionally excluded — that's a
    # passthrough from the metadata service. DataDescription has no `notes`
    # field, so we stamp `data_summary` instead.
    procedures.notes = augment_notes(procedures.notes)
    acquisition.notes = augment_notes(acquisition.notes)
    dd.data_summary = augment_notes(dd.data_summary)

    procedures.write_standard_file(output_directory=RESULTS_DIR)
    acquisition.write_standard_file(output_directory=RESULTS_DIR)
    subject.write_standard_file(output_directory=RESULTS_DIR)
    dd.write_standard_file(output_directory=RESULTS_DIR)

    print(f"  procedures.json:        {len(procedures.subject_procedures)} subject + {len(procedures.specimen_procedures)} specimen procedures")
    print(f"  acquisition.json:       {len(acquisition.specimen_id)} specimens")
    print(f"  subject.json:           written")
    print(f"  data_description.json:  name={dd.name!r}")

    asset = _find_input_asset(subject_id)
    if asset is None:
        print(
            f"  WARNING: no input asset matching {subject_id}_* in {DATA_DIR}. "
            f"Skipping raw data copy. (Expected on Code Ocean — set up the App "
            f"Panel parameters and attach the right asset; benign if you're "
            f"running locally without /data/ mounted.)"
        )
    else:
        _copy_modality_data(asset, modality, RESULTS_DIR)

    print(f"\nWrote bundle for {subject_id}/{modality} to {RESULTS_DIR}")


if __name__ == "__main__":
    args = _parse_args()
    run(args.subject_id, args.modality)
