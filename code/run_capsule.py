"""Top-level run script.

Iterates the SUBJECTS dict, builds Procedures + MAPseq + BARseq Acquisition
objects for each, validates each via JSON round-trip, and writes the JSON
files to /results/<subject_id>/<modality>/.

For each (subject, modality), the result folder ends up self-contained with
the four metadata files needed to upload as a DocDB data asset:

    procedures.json          (locally-built sectioning + service-fetched injections)
    acquisition.json         (modality-specific)
    subject.json             (broadcast — modality-independent, fetched from service)
    data_description.json    (modality-specific, prebuilt by prefetch_inputs.py)

`procedures.json` and `subject.json` are duplicated between the mapseq/ and
barseq/ folders for a given subject because each modality folder is meant
to ship as a stand-alone bundle.

Output layout (per subject):
    <subject>/mapseq/{procedures,acquisition,subject,data_description}.json
    <subject>/barseq/{procedures,acquisition,subject,data_description}.json
"""

import os
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


def _load_inputs(subject_id: str):
    """Load the prefetched inputs for one subject.

    Args:
        subject_id: Subject ID (e.g. "780345").

    Returns:
        Tuple of (Subject, Procedures, DataDescription, DataDescription) where
        the two DataDescription instances are MAPseq and BARseq in that order.
        The Procedures returned here is the *service* version — it carries the
        injections we need to merge into the locally-built procedures.
    """
    subj_dir = INPUTS_DIR / subject_id
    subject = Subject.model_validate_json((subj_dir / "subject.json").read_text())
    service_proc = Procedures.model_validate_json((subj_dir / "procedures_from_service.json").read_text())
    mapseq_dd = DataDescription.model_validate_json((subj_dir / "mapseq" / "data_description.json").read_text())
    barseq_dd = DataDescription.model_validate_json((subj_dir / "barseq" / "data_description.json").read_text())
    return subject, service_proc, mapseq_dd, barseq_dd


def run() -> None:
    """Build and write the per-modality metadata bundle for every subject in SUBJECTS.

    For each subject, loads its prefetched inputs (subject.json, the service
    procedures.json containing injections, and a data_description.json per
    modality), builds the locally-generated sectioning Procedures and the two
    Acquisitions, merges the service's `subject_procedures` into the local
    procedures, validates each via JSON round-trip, and writes the four
    metadata files into each modality folder.

    Reads `CO_RESULTS_DIR` from the environment to override the default `/results`.
    Has no return value; results are observed via files written under `RESULTS_DIR`
    and a per-subject summary printed to stdout.
    """
    for subject_id, cfg in SUBJECTS.items():
        print(f"=== {subject_id} ===")
        mapseq_dir = RESULTS_DIR / subject_id / "mapseq"
        barseq_dir = RESULTS_DIR / subject_id / "barseq"
        mapseq_dir.mkdir(parents=True, exist_ok=True)
        barseq_dir.mkdir(parents=True, exist_ok=True)

        subject, service_proc, mapseq_dd, barseq_dd = _load_inputs(subject_id)

        local_proc = build_procedures(subject_id, cfg)
        merged_proc = local_proc.model_copy(
            update={"subject_procedures": service_proc.subject_procedures}
        )

        procedures = _validate_roundtrip(merged_proc, Procedures)
        mapseq_acq = _validate_roundtrip(build_acquisition(subject_id, cfg, procedures, "MAPseq"), Acquisition)
        barseq_acq = _validate_roundtrip(build_acquisition(subject_id, cfg, procedures, "BARseq"), Acquisition)

        # Stamp the provenance URL onto every artifact this capsule actually
        # generates or assembles, so any downstream reader can trace it back
        # to the code that produced it. subject.json is intentionally
        # excluded — that's a passthrough from the metadata service, not
        # something this capsule authored. DataDescription has no `notes`
        # field, so we augment `data_summary` for those.
        procedures.notes = augment_notes(procedures.notes)
        mapseq_acq.notes = augment_notes(mapseq_acq.notes)
        barseq_acq.notes = augment_notes(barseq_acq.notes)
        mapseq_dd.data_summary = augment_notes(mapseq_dd.data_summary)
        barseq_dd.data_summary = augment_notes(barseq_dd.data_summary)

        for d in (mapseq_dir, barseq_dir):
            procedures.write_standard_file(output_directory=d)
            subject.write_standard_file(output_directory=d)
        mapseq_dd.write_standard_file(output_directory=mapseq_dir)
        barseq_dd.write_standard_file(output_directory=barseq_dir)
        mapseq_acq.write_standard_file(output_directory=mapseq_dir)
        barseq_acq.write_standard_file(output_directory=barseq_dir)

        print(f"  procedures.json:         {len(procedures.subject_procedures)} subject + {len(procedures.specimen_procedures)} specimen procedures")
        print(f"  mapseq/acquisition.json: {len(mapseq_acq.specimen_id)} specimens")
        print(f"  barseq/acquisition.json: {len(barseq_acq.specimen_id)} specimens")
        print(f"  subject.json + data_description.json broadcast to both modality folders")

    print(f"\nWrote {len(SUBJECTS)} subject(s) to {RESULTS_DIR}")


if __name__ == "__main__":
    run()
