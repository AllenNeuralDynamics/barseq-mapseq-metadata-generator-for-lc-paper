"""Build the per-modality JobSettings file consumed by aind-metadata-mapper's
gather_metadata job.

Public entry point:
    build_gather_metadata_settings(subject_id, modality) -> dict

The settings file lives next to acquisition.json in each modality folder so
a downstream operator can run gather_metadata locally to fetch subject.json
and complete data_description.json from the on-prem AIND metadata service.
"""

# Project name used by gather_metadata to look up funding sources and
# investigators from the AIND metadata service
# (/api/v2/funding/{project_name} and /api/v2/investigators/{project_name}).
# Must match the project name registered in that service exactly, otherwise
# both fields come back empty.
PROJECT_NAME: str = "Discovery-Neuromodulator circuit dynamics during foraging - Subproject 2 Molecular Anatomy Cell Types"

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


def build_gather_metadata_settings(subject_id: str, modality: str) -> dict:
    """Build a JobSettings dict for aind-metadata-mapper's gather_metadata job.

    `acquisition_start_time` is intentionally omitted — gather_metadata reads
    it from the acquisition.json sitting in the same folder.

    Args:
        subject_id: Subject ID (e.g. "780345").
        modality: Either "MAPseq" or "BARseq" (must match `Modality.from_abbreviation`).

    Returns:
        A plain dict suitable for `JobSettings.model_validate_json(json.dumps(...))`.
        Output dir is `"."` so the job is meant to be run from inside the modality
        folder this file is written to.

    Raises:
        ValueError: if `modality` is not "MAPseq" or "BARseq".
    """
    if modality == "MAPseq":
        data_summary = _MAPSEQ_DATA_SUMMARY
    elif modality == "BARseq":
        data_summary = _BARSEQ_DATA_SUMMARY
    else:
        raise ValueError(f"Unknown modality: {modality}")
    return {
        "output_dir": ".",
        "subject_id": subject_id,
        "data_description_settings": {
            "project_name": PROJECT_NAME,
            "modalities": [modality],
            "data_summary": data_summary,
        },
    }
