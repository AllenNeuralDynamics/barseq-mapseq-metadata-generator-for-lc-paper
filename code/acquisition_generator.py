"""Build the per-modality Acquisition objects.

Public entry points:
    build_mapseq_acquisition(subject_id, cfg, procedures) -> Acquisition
    build_barseq_acquisition(subject_id, cfg, procedures) -> Acquisition

Both acquisitions derive their `specimen_id` from the same Procedures
object (via mapseq_specimen_ids / barseq_specimen_ids) so the two artifacts
stay in sync by construction.
"""

from typing import List

from aind_data_schema_models.modalities import Modality

from aind_data_schema.core.acquisition import Acquisition, ExternalDataStream
from aind_data_schema.core.procedures import Procedures

from procedures_generator import barseq_specimen_ids, mapseq_specimen_ids
from provenance import augment_notes

# ---------------------------------------------------------------------------
# Acquisition constants
# ---------------------------------------------------------------------------
_BARSEQ_PROTOCOL_ID = ["https://www.protocols.io/view/barseq-2-5-kqdg3ke9qv25/v1"]
_MAPSEQ_PROTOCOL_ID: List[str] = []  # No published MAPseq protocol URL.

_MAPSEQ_ACQUISITION_NOTE = (
    "MAPseq was performed off-site at Cold Spring Harbor Laboratory. "
    "The acquisition_start_time represents the date the tissue was mailed to "
    "CSHL; the acquisition_end_time represents the date the final processed "
    "results were received."
)
_MAPSEQ_STREAM_NOTE = "Acquired off-site at Cold Spring Harbor Laboratory."

_BARSEQ_ACQUISITION_NOTE = (
    "BARseq acquisition performed across multiple slides imaged over multiple days. "
    "Full acquisition includes gene sequencing (7 cycles), barcode sequencing (15 cycles), "
    "and one hybridization cycle. Each slide folder contains all three acquisition types. "
    "Final processed output is a cell x gene x barcode table registered to Allen CCFv3."
)
_BARSEQ_STREAM_NOTE = "Acquired by the Allen Institute for Brain Science BARseq imaging team."


def build_mapseq_acquisition(
    subject_id: str,
    cfg: dict,
    procedures: Procedures,
) -> Acquisition:
    start = cfg["mapseq_start"]
    end = cfg["mapseq_end"]
    return Acquisition(
        subject_id=subject_id,
        specimen_id=mapseq_specimen_ids(procedures),
        acquisition_start_time=start,
        acquisition_end_time=end,
        experimenters=cfg["mapseq_experimenters"],
        protocol_id=_MAPSEQ_PROTOCOL_ID,
        acquisition_type="BarcodeSequencing",
        notes=augment_notes(_MAPSEQ_ACQUISITION_NOTE),
        data_streams=[
            ExternalDataStream(
                stream_start_time=start,
                stream_end_time=end,
                modalities=[Modality.MAPSEQ],
                notes=_MAPSEQ_STREAM_NOTE,
            )
        ],
    )


def build_barseq_acquisition(
    subject_id: str,
    cfg: dict,
    procedures: Procedures,
) -> Acquisition:
    start = cfg["barseq_start"]
    end = cfg["barseq_end"]
    return Acquisition(
        subject_id=subject_id,
        specimen_id=barseq_specimen_ids(procedures),
        acquisition_start_time=start,
        acquisition_end_time=end,
        experimenters=cfg["barseq_experimenters"],
        protocol_id=_BARSEQ_PROTOCOL_ID,
        acquisition_type="BarcodeSequencing",
        notes=augment_notes(_BARSEQ_ACQUISITION_NOTE),
        data_streams=[
            ExternalDataStream(
                stream_start_time=start,
                stream_end_time=end,
                modalities=[Modality.BARSEQ],
                notes=_BARSEQ_STREAM_NOTE,
            )
        ],
    )
