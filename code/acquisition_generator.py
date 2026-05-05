"""Build the per-modality Acquisition objects.

Public entry point:
    build_acquisition(subject_id, cfg, procedures, modality) -> Acquisition

The two modalities (MAPseq, BARseq) share a single builder; per-modality data
(cfg keys, specimen-id collector, protocol ID, notes, Modality enum) lives in
`_MODALITY_CONFIG`. Both acquisitions derive their `specimen_id` from the same
Procedures object so the two artifacts stay in sync by construction.
"""

from aind_data_schema_models.modalities import Modality

from aind_data_schema.core.acquisition import Acquisition, ExternalDataStream
from aind_data_schema.core.procedures import Procedures

from procedures_generator import barseq_specimen_ids, mapseq_specimen_ids
from provenance import augment_notes

_MAPSEQ_ACQUISITION_NOTE = (
    "MAPseq was performed off-site at Cold Spring Harbor Laboratory. "
    "The acquisition_start_time represents the date the tissue was mailed to "
    "CSHL; the acquisition_end_time represents the date the final processed "
    "results were received."
)
_BARSEQ_ACQUISITION_NOTE = (
    "BARseq acquisition performed across multiple slides imaged over multiple days. "
    "Full acquisition includes gene sequencing (7 cycles), barcode sequencing (15 cycles), "
    "and one hybridization cycle. Each slide folder contains all three acquisition types. "
    "Final processed output is a cell x gene x barcode table registered to Allen CCFv3."
)

_MODALITY_CONFIG = {
    "MAPseq": {
        "modality": Modality.MAPSEQ,
        "cfg_start": "mapseq_start",
        "cfg_end": "mapseq_end",
        "cfg_experimenters": "mapseq_experimenters",
        "specimen_ids": mapseq_specimen_ids,
        "protocol_id": [],  # No published MAPseq protocol URL.
        "acquisition_note": _MAPSEQ_ACQUISITION_NOTE,
        "stream_note": "Acquired off-site at Cold Spring Harbor Laboratory.",
    },
    "BARseq": {
        "modality": Modality.BARSEQ,
        "cfg_start": "barseq_start",
        "cfg_end": "barseq_end",
        "cfg_experimenters": "barseq_experimenters",
        "specimen_ids": barseq_specimen_ids,
        "protocol_id": ["https://www.protocols.io/view/barseq-2-5-kqdg3ke9qv25/v1"],
        "acquisition_note": _BARSEQ_ACQUISITION_NOTE,
        "stream_note": "Acquired by the Allen Institute for Brain Science BARseq imaging team.",
    },
}


def build_acquisition(
    subject_id: str,
    cfg: dict,
    procedures: Procedures,
    modality: str,
) -> Acquisition:
    """Build the per-modality Acquisition for one subject.

    Args:
        subject_id: Subject ID (e.g. "780345").
        cfg: Per-subject config from `subjects.SUBJECTS`. The relevant keys
            depend on `modality` and are read via `_MODALITY_CONFIG` (e.g.
            `mapseq_start`/`mapseq_end`/`mapseq_experimenters` for MAPseq).
        procedures: Procedures model built by `build_procedures` for the same
            subject; used to derive the `specimen_id` list.
        modality: Either "MAPseq" or "BARseq".

    Returns:
        An Acquisition model with `acquisition_type="BarcodeSequencing"`, the
        chosen `Modality`, an `ExternalDataStream`, and notes that carry the
        provenance stamp if `PROVENANCE_URL` is set.

    Raises:
        KeyError: if `modality` is not "MAPseq" or "BARseq".
    """
    modality_cfg = _MODALITY_CONFIG[modality]
    start = cfg[modality_cfg["cfg_start"]]
    end = cfg[modality_cfg["cfg_end"]]
    return Acquisition(
        subject_id=subject_id,
        specimen_id=modality_cfg["specimen_ids"](procedures),
        acquisition_start_time=start,
        acquisition_end_time=end,
        experimenters=cfg[modality_cfg["cfg_experimenters"]],
        protocol_id=modality_cfg["protocol_id"],
        acquisition_type="BarcodeSequencing",
        notes=augment_notes(modality_cfg["acquisition_note"]),
        data_streams=[
            ExternalDataStream(
                stream_start_time=start,
                stream_end_time=end,
                modalities=[modality_cfg["modality"]],
                notes=modality_cfg["stream_note"],
            )
        ],
    )
