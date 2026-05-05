"""Prefetch metadata files that depend on the AIND on-prem metadata service.

Run this once before publishing a Code Ocean release, or whenever upstream
data changes (subject genotype corrected, new investigator on the project,
new injection added). Output goes to `code/inputs/`, which is committed to
the repo. The capsule reads those files at run time and merges them with
the procedures and acquisitions it generates locally.

Produces:

    code/inputs/<subject_id>/
        subject.json                      # from /api/v2/subject
        procedures_from_service.json      # from /api/v2/procedures (we use the
                                          # subject_procedures = injections)
        mapseq/data_description.json      # built by gather_metadata using
        barseq/data_description.json      # /api/v2/funding + /api/v2/investigators

Requires network access to http://aind-metadata-service. Run with:

    cd code
    uv run --with aind-metadata-mapper --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev python prefetch_inputs.py
"""

import json
import tempfile
from pathlib import Path

from aind_data_schema.core.data_description import build_data_name
from aind_metadata_mapper.gather_metadata import GatherMetadataJob
from aind_metadata_mapper.models import DataDescriptionSettings, JobSettings

from subjects import SUBJECTS

PROJECT_NAME = "Discovery-Neuromodulator circuit dynamics during foraging - Subproject 2 Molecular Anatomy Cell Types"

_MAPSEQ_DATA_SUMMARY = (
    "MAPseq projection mapping data for the locus coeruleus (LC) paper. "
    "Brain sections were cut at the Allen Institute, chunked by brain region, "
    "and shipped to Cold Spring Harbor Laboratory for sequencing. The asset "
    "contains per-chunk barcode counts used to reconstruct projections from "
    "LC neurons across the brain."
)
_BARSEQ_DATA_SUMMARY = (
    "BARseq spatial sequencing data for the locus coeruleus (LC) paper. "
    "LC sections were imaged in-house at the Allen Institute across gene-"
    "sequencing (7 cycles), barcode-sequencing (15 cycles), and one "
    "hybridization cycle. The asset contains a cell x gene x barcode table "
    "registered to the Allen CCFv3."
)

DATA_SUMMARIES = {"MAPseq": _MAPSEQ_DATA_SUMMARY, "BARseq": _BARSEQ_DATA_SUMMARY}
START_KEYS = {"MAPseq": "mapseq_start", "BARseq": "barseq_start"}

INPUTS_DIR = Path(__file__).parent / "inputs"


def _make_job(subject_id: str, modality: str, output_dir: str) -> GatherMetadataJob:
    """Construct a GatherMetadataJob configured for one (subject, modality).

    Args:
        subject_id: Subject ID (e.g. "780345").
        modality: "MAPseq" or "BARseq".
        output_dir: Required by JobSettings; we pass a throwaway temp dir
            because we call get_subject / get_procedures / build_data_description
            directly and save the returned dicts ourselves.

    Returns:
        A configured GatherMetadataJob ready for direct method calls.
    """
    return GatherMetadataJob(
        settings=JobSettings(
            output_dir=output_dir,
            subject_id=subject_id,
            data_description_settings=DataDescriptionSettings(
                project_name=PROJECT_NAME,
                modalities=[modality],
                data_summary=DATA_SUMMARIES[modality],
            ),
        )
    )


def _write_json(path: Path, contents: dict) -> None:
    """Write a dict as indented JSON, creating parent directories as needed.

    Args:
        path: Destination file path.
        contents: JSON-serializable dict to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contents, indent=3))


def main() -> None:
    """Fetch subject + procedures + per-modality data_description for every subject in SUBJECTS.

    Writes everything under `code/inputs/`. Uses a fresh tempdir as
    gather_metadata's output_dir to avoid the "use existing file" code path
    that would skip refetching from the service.
    """
    for subject_id, cfg in SUBJECTS.items():
        print(f"=== {subject_id} ===")
        subject_dir = INPUTS_DIR / subject_id

        with tempfile.TemporaryDirectory() as tmp:
            job = _make_job(subject_id, "MAPseq", tmp)

            subject = job.get_subject(subject_id)
            if subject is None:
                raise RuntimeError(f"Could not fetch subject {subject_id} from metadata service")
            _write_json(subject_dir / "subject.json", subject)
            print("  fetched subject")

            procedures = job.get_procedures(subject_id)
            if procedures is None:
                raise RuntimeError(f"Could not fetch procedures for {subject_id}")
            _write_json(subject_dir / "procedures_from_service.json", procedures)
            print(f"  fetched procedures ({len(procedures.get('subject_procedures', []))} subject_procedures)")

            for modality in ("MAPseq", "BARseq"):
                mod_job = _make_job(subject_id, modality, tmp)
                acq_start = cfg[START_KEYS[modality]]
                dd = mod_job.build_data_description(
                    acquisition_start_time=acq_start.isoformat(),
                    subject_id=subject_id,
                )
                # Override the auto-generated name. By default it's just
                # `<subject>_<acq_time>`; AIND convention for raw-data assets
                # is `<modality>_<subject>_<acq_time>` so the modality is
                # legible at a glance in the asset name.
                dd["name"] = build_data_name(f"{modality.lower()}_{subject_id}", acq_start)
                _write_json(subject_dir / modality.lower() / "data_description.json", dd)
                print(f"  built {modality.lower()}/data_description.json (name={dd['name']!r})")


if __name__ == "__main__":
    main()
