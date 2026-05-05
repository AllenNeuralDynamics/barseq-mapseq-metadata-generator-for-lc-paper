"""Build the per-subject Procedures object.

Public entry points:
    build_procedures(subject_id, cfg) -> Procedures
    mapseq_specimen_ids(procedures) -> list[str]
    barseq_specimen_ids(procedures) -> list[str]

The acquisition builders import the two specimen-id functions to derive
their `specimen_id` lists directly from the Procedures object — that way
acquisition and procedures stay in sync by construction.
"""

import re
from typing import Dict, List

from aind_data_schema_models.brain_atlas import CCFv3
from aind_data_schema_models.units import SizeUnit

from aind_data_schema.components.coordinates import AtlasLibrary
from aind_data_schema.components.specimen_procedures import (
    PlanarSectioning,
    Section,
    Sectioning,
    SpecimenProcedure,
)
from aind_data_schema.core.procedures import Procedures

from _procedures_helpers import (
    create_nonuniform_sections,
    create_planar_sectioning,
    create_uniform_sections,
)

# ---------------------------------------------------------------------------
# Sectioning constants (shared across subjects)
# ---------------------------------------------------------------------------
_MAPSEQ_FIRST_BATCH_SPAN_UM = 9800       # spread across plates 0-98
_MAPSEQ_SECOND_BATCH_ORIGIN_UM = 11200   # plates 112+
_MAPSEQ_SECOND_BATCH_SPAN_UM = 2000      # spread across plates 112-132
_MAPSEQ_THICKNESS_UM = 300               # partial slices for both batches
_BARSEQ_START_UM = 9900                  # LC range begins here
_BARSEQ_THICKNESS_UM = 20                # uniform spacing
_SPINAL_THICKNESS_UM = 1000              # approximate

_SECTIONING_EXPERIMENTERS = ["Polina Kosillo"]

# ---------------------------------------------------------------------------
# Specimen-id pattern filters
# ---------------------------------------------------------------------------
# MAPseq acquisition includes everything sent to CSHL for sequencing:
#   * brain-region chunks (e.g. 780345_map001_001), and
#   * the spinal cord (e.g. 780345_spinal).
# The slide-level IDs (780345_map001 etc.) are intermediate products and
# are excluded by the strict `type(detail) is Sectioning` check elsewhere
# (those come from PlanarSectioning, which subclasses Sectioning).
_MAPSEQ_OUTPUT_PATTERN = re.compile(r"(_map\d{3}_\d{3}|_spinal)$")
_BAR_PATTERN = re.compile(r"_bar\d{3}$")          # e.g. 780345_bar001

# ---------------------------------------------------------------------------
# MAPseq slide-region chunking data (which brain regions each slide is
# chunked into for the LC-paper subjects).
# ---------------------------------------------------------------------------
_SLIDE_REGIONS = [
    {"slide_num": 1, "section_start": 1, "section_end": 3, "chunk_name": "MOB", "ccf_acronym": "MOB", "includes_surrounding_tissue": False, "notes": "Main olfactory bulb"},
    {"slide_num": 2, "section_start": 4, "section_end": 6, "chunk_name": "MOB", "ccf_acronym": "MOB", "includes_surrounding_tissue": False, "notes": "Main olfactory bulb"},
    {"slide_num": 3, "section_start": 7, "section_end": 9, "chunk_name": "ORB", "ccf_acronym": "ORB", "includes_surrounding_tissue": False, "notes": "Orbital area (orbitofrontal cortex)"},
    {"slide_num": 3, "section_start": 7, "section_end": 9, "chunk_name": "MO", "ccf_acronym": "MO", "includes_surrounding_tissue": False, "notes": "Somatomotor areas (motor cortex)"},
    {"slide_num": 3, "section_start": 7, "section_end": 9, "chunk_name": "AON", "ccf_acronym": "AON", "includes_surrounding_tissue": False, "notes": "Anterior olfactory nucleus"},
    {"slide_num": 4, "section_start": 10, "section_end": 12, "chunk_name": "ORB", "ccf_acronym": "ORB", "includes_surrounding_tissue": False, "notes": "Orbital area (orbitofrontal cortex)"},
    {"slide_num": 4, "section_start": 10, "section_end": 12, "chunk_name": "MO", "ccf_acronym": "MO", "includes_surrounding_tissue": False, "notes": "Somatomotor areas (motor cortex)"},
    {"slide_num": 4, "section_start": 10, "section_end": 12, "chunk_name": "AON", "ccf_acronym": "AON", "includes_surrounding_tissue": False, "notes": "Anterior olfactory nucleus"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "CP", "ccf_acronym": "CP", "includes_surrounding_tissue": False, "notes": "Caudoputamen"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "ACB", "ccf_acronym": "ACB", "includes_surrounding_tissue": False, "notes": "Nucleus accumbens"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "LSX", "ccf_acronym": "LSX", "includes_surrounding_tissue": False, "notes": "Lateral septal complex"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "ctx_1", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Superior/dorsal cortex ribbon (ctx 1 in figure)"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "ctx_2", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Lateral cortex ribbon (ctx 2 in figure)"},
    {"slide_num": 5, "section_start": 13, "section_end": 15, "chunk_name": "ctx_3", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Inferior/ventrolateral cortex ribbon (ctx 3 in figure)"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "CP", "ccf_acronym": "CP", "includes_surrounding_tissue": False, "notes": "Caudoputamen"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "ACB", "ccf_acronym": "ACB", "includes_surrounding_tissue": False, "notes": "Nucleus accumbens"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "LSX", "ccf_acronym": "LSX", "includes_surrounding_tissue": False, "notes": "Lateral septal complex"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "ctx_1", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Superior/dorsal cortex ribbon (ctx 1 in figure)"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "ctx_2", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Lateral cortex ribbon (ctx 2 in figure)"},
    {"slide_num": 6, "section_start": 16, "section_end": 18, "chunk_name": "ctx_3", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Inferior/ventrolateral cortex ribbon (ctx 3 in figure)"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "CP", "ccf_acronym": "CP", "includes_surrounding_tissue": False, "notes": "Caudoputamen"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "LSX", "ccf_acronym": "LSX", "includes_surrounding_tissue": False, "notes": "Lateral septal complex"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "BST", "ccf_acronym": "BST", "includes_surrounding_tissue": False, "notes": "Bed nuclei of the stria terminalis (BNST)"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "ctx_1", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Superior/dorsal cortex ribbon (ctx 1 in figure)"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "ctx_2", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Lateral cortex ribbon (ctx 2 in figure)"},
    {"slide_num": 7, "section_start": 19, "section_end": 21, "chunk_name": "ctx_3", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Inferior/ventrolateral cortex ribbon (ctx 3 in figure)"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "HPF", "ccf_acronym": "HPF", "includes_surrounding_tissue": False, "notes": "Hippocampal formation"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "TH", "ccf_acronym": "TH", "includes_surrounding_tissue": False, "notes": "Thalamus"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "HY", "ccf_acronym": "HY", "includes_surrounding_tissue": False, "notes": "Hypothalamus"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "amygdala", "ccf_acronym": "BLA", "includes_surrounding_tissue": True, "notes": "Amygdala (targeting whole structure via BLA + surrounding tissue)"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "GPE", "ccf_acronym": "GPe", "includes_surrounding_tissue": False, "notes": "Globus pallidus external segment (GPe)"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "ctx_1", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Superior/dorsal cortex ribbon (ctx 1 in figure)"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "ctx_2", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Lateral cortex ribbon (ctx 2 in figure)"},
    {"slide_num": 8, "section_start": 22, "section_end": 24, "chunk_name": "ctx_3", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Inferior/ventrolateral cortex ribbon (ctx 3 in figure)"},
    {"slide_num": 9, "section_start": 25, "section_end": 27, "chunk_name": "MB", "ccf_acronym": "MB", "includes_surrounding_tissue": False, "notes": "Midbrain"},
    {"slide_num": 9, "section_start": 25, "section_end": 27, "chunk_name": "ctx_1", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Superior/dorsal cortex ribbon (ctx 1 in figure)"},
    {"slide_num": 9, "section_start": 25, "section_end": 27, "chunk_name": "ctx_2", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Lateral cortex ribbon (ctx 2 in figure)"},
    {"slide_num": 9, "section_start": 25, "section_end": 27, "chunk_name": "ctx_3", "ccf_acronym": "CTX", "includes_surrounding_tissue": True, "notes": "Inferior/ventrolateral cortex ribbon (ctx 3 in figure)"},
    {"slide_num": 10, "section_start": 28, "section_end": 30, "chunk_name": "MB", "ccf_acronym": "MB", "includes_surrounding_tissue": False, "notes": "Midbrain (more caudal)"},
    {"slide_num": 10, "section_start": 28, "section_end": 30, "chunk_name": "HB", "ccf_acronym": "HB", "includes_surrounding_tissue": False, "notes": "Hindbrain"},
    {"slide_num": 11, "section_start": 31, "section_end": 33, "chunk_name": "MB", "ccf_acronym": "MB", "includes_surrounding_tissue": False, "notes": "Midbrain (most caudal)"},
    {"slide_num": 11, "section_start": 31, "section_end": 33, "chunk_name": "HB", "ccf_acronym": "HB", "includes_surrounding_tissue": False, "notes": "Hindbrain"},
    {"slide_num": 12, "section_start": 34, "section_end": 36, "chunk_name": "CB", "ccf_acronym": "CB", "includes_surrounding_tissue": False, "notes": "Cerebellum"},
    {"slide_num": 12, "section_start": 34, "section_end": 36, "chunk_name": "MY", "ccf_acronym": "MY", "includes_surrounding_tissue": False, "notes": "Medulla"},
    {"slide_num": 13, "section_start": 37, "section_end": 39, "chunk_name": "MY", "ccf_acronym": "MY", "includes_surrounding_tissue": False, "notes": "Medulla"},
]


def _load_slide_regions() -> Dict[int, dict]:
    """Group the flat _SLIDE_REGIONS rows by slide number.

    Returns:
        Dict keyed by slide number. Each value has `section_start`, `section_end`,
        and a `chunks` list (one entry per brain-region chunk cut from that slide).
    """
    slides: Dict[int, dict] = {}
    for row in _SLIDE_REGIONS:
        slide = row["slide_num"]
        if slide not in slides:
            slides[slide] = {
                "section_start": row["section_start"],
                "section_end": row["section_end"],
                "chunks": [],
            }
        slides[slide]["chunks"].append(
            {
                "chunk_name": row["chunk_name"],
                "ccf_acronym": row["ccf_acronym"],
                "includes_surrounding_tissue": row["includes_surrounding_tissue"],
                "notes": row["notes"],
            }
        )
    return slides


def _generate_mapseq_slide_chunks(specimen_id: str, sectioning_date) -> List[SpecimenProcedure]:
    """One SpecimenProcedure per MAPseq slide, capturing the brain-region chunks cut from it.

    Args:
        specimen_id: Subject ID; used as the prefix for input slice IDs and chunk IDs.
        sectioning_date: Date of the chunking; written to start_date and end_date.

    Returns:
        A list of SpecimenProcedure models — one per slide in `_SLIDE_REGIONS`.
        Each has procedure_type="Sectioning" and a single Sectioning detail whose
        sections are the per-chunk outputs (e.g. `<specimen_id>_map001_001`).
    """
    slides = _load_slide_regions()
    procedures = []
    for slide_num, slide_data in slides.items():
        section_start = slide_data["section_start"]
        section_end = slide_data["section_end"]
        chunks = slide_data["chunks"]

        input_ids = [f"{specimen_id}_map{i:03d}" for i in range(section_start, section_end + 1)]

        output_sections = []
        for chunk_idx, chunk in enumerate(chunks, start=1):
            structure = CCFv3.by_acronym(chunk["ccf_acronym"])
            surrounding = True if chunk["includes_surrounding_tissue"] else None
            for sec_id in input_ids:
                output_sections.append(
                    Section(
                        output_specimen_id=f"{sec_id}_{chunk_idx:03d}",
                        targeted_structure=structure,
                        includes_surrounding_tissue=surrounding,
                    )
                )

        chunk_names = ", ".join(c["chunk_name"] for c in chunks)
        ctx_notes = "; ".join(c["notes"] for c in chunks if c["ccf_acronym"] == "CTX")
        note = f"Slide {slide_num}: sections {section_start}-{section_end} chunked into [{chunk_names}]"
        if ctx_notes:
            note += f". CTX chunks: {ctx_notes}"

        procedures.append(
            SpecimenProcedure(
                procedure_type="Sectioning",
                specimen_id=input_ids,
                start_date=sectioning_date,
                end_date=sectioning_date,
                experimenters=_SECTIONING_EXPERIMENTERS,
                procedure_details=[Sectioning(sections=output_sections)],
                notes=note,
            )
        )
    return procedures


# ---------------------------------------------------------------------------
# Sectioning sub-procedure builders
# ---------------------------------------------------------------------------
def _mapseq_first_batch(subject_id: str, cfg: dict) -> PlanarSectioning:
    """Build the MAPseq first-batch PlanarSectioning (sections 1..mapseq_first_batch_count).

    Args:
        subject_id: Subject ID, used as the prefix on each PlanarSection.
        cfg: Per-subject config; reads `mapseq_first_batch_count`.

    Returns:
        PlanarSectioning with `cfg["mapseq_first_batch_count"]` non-uniform partial
        slices spread across `_MAPSEQ_FIRST_BATCH_SPAN_UM`.
    """
    n = cfg["mapseq_first_batch_count"]
    starts = [i * (_MAPSEQ_FIRST_BATCH_SPAN_UM / n) for i in range(n)]
    sections = create_nonuniform_sections(
        specimen_id=subject_id,
        num_sections=n,
        start_positions_um=starts,
        thickness=_MAPSEQ_THICKNESS_UM,
        thickness_unit=SizeUnit.UM,
        section_prefix="map",
        start_section_num=1,
    )
    return create_planar_sectioning(sections)


def _mapseq_second_batch(subject_id: str, cfg: dict) -> PlanarSectioning:
    """Build the MAPseq second-batch PlanarSectioning (continues numbering after the first batch).

    Args:
        subject_id: Subject ID, used as the prefix on each PlanarSection.
        cfg: Per-subject config; reads `mapseq_first_batch_count` and `mapseq_second_batch_count`.

    Returns:
        PlanarSectioning with `cfg["mapseq_second_batch_count"]` non-uniform partial
        slices spread across `_MAPSEQ_SECOND_BATCH_SPAN_UM`, starting at
        `_MAPSEQ_SECOND_BATCH_ORIGIN_UM` and numbered after the first batch.
    """
    n = cfg["mapseq_second_batch_count"]
    start = cfg["mapseq_first_batch_count"] + 1
    starts = [
        _MAPSEQ_SECOND_BATCH_ORIGIN_UM + i * (_MAPSEQ_SECOND_BATCH_SPAN_UM / n)
        for i in range(n)
    ]
    sections = create_nonuniform_sections(
        specimen_id=subject_id,
        num_sections=n,
        start_positions_um=starts,
        thickness=_MAPSEQ_THICKNESS_UM,
        thickness_unit=SizeUnit.UM,
        section_prefix="map",
        start_section_num=start,
    )
    return create_planar_sectioning(sections)


def _barseq_lc(subject_id: str, cfg: dict) -> PlanarSectioning:
    """Build the BARseq LC-section PlanarSectioning (uniform slicing through the LC range).

    Args:
        subject_id: Subject ID, used as the prefix on each PlanarSection.
        cfg: Per-subject config; reads `barseq_count`.

    Returns:
        PlanarSectioning with `cfg["barseq_count"]` uniform LC sections starting
        at `_BARSEQ_START_UM`, each `_BARSEQ_THICKNESS_UM` thick.
    """
    sections = create_uniform_sections(
        specimen_id=subject_id,
        start_section_num=1,
        num_sections=cfg["barseq_count"],
        start_um=_BARSEQ_START_UM,
        thickness=_BARSEQ_THICKNESS_UM,
        thickness_unit=SizeUnit.UM,
        section_prefix="bar",
    )
    return create_planar_sectioning(sections)


def _spinal(subject_id: str, cfg: dict) -> Sectioning:
    """Build the MAPseq spinal-cord Sectioning (one or more Sections sharing one output ID).

    Args:
        subject_id: Subject ID; used to form `<subject_id>_spinal`.
        cfg: Per-subject config; reads `spinal_section_count` (number of Section entries).

    Returns:
        A Sectioning whose Sections all share `output_specimen_id="<subject_id>_spinal"`.
    """
    return Sectioning(
        sections=[
            Section(
                output_specimen_id=f"{subject_id}_spinal",
                targeted_structure=CCFv3.CST,
                thickness=_SPINAL_THICKNESS_UM,
                thickness_unit=SizeUnit.UM,
            )
            for _ in range(cfg["spinal_section_count"])
        ]
    )


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------
def build_procedures(subject_id: str, cfg: dict) -> Procedures:
    """Build the full Procedures object for one subject.

    Combines the four LC-paper sectioning sub-procedures (MAPseq first batch,
    BARseq LC, MAPseq second batch, spinal cord) with one SpecimenProcedure per
    MAPseq slide describing how that slide was chunked into brain-region pieces.

    Args:
        subject_id: Subject ID (e.g. "780345").
        cfg: Per-subject config from `subjects.SUBJECTS`. Reads `mapseq_first_batch_count`,
            `mapseq_second_batch_count`, `barseq_count`, `spinal_section_count`, and
            `sectioning_date`.

    Returns:
        A Procedures model. For the LC paper this is 17 SpecimenProcedures
        (4 batch-level + 13 slide-chunk SpecimenProcedures).
    """
    n_first = cfg["mapseq_first_batch_count"]
    n_second = cfg["mapseq_second_batch_count"]
    sectioning_date = cfg["sectioning_date"]
    return Procedures(
        subject_id=subject_id,
        coordinate_system=AtlasLibrary.CCFv3_10um,
        specimen_procedures=[
            SpecimenProcedure(
                procedure_type="Sectioning",
                specimen_id=subject_id,
                start_date=sectioning_date,
                end_date=sectioning_date,
                experimenters=_SECTIONING_EXPERIMENTERS,
                procedure_details=[_mapseq_first_batch(subject_id, cfg)],
                notes=f"MAPseq first batch: sections 1-{n_first} ({_MAPSEQ_THICKNESS_UM}um thick, partial slices)",
            ),
            SpecimenProcedure(
                procedure_type="Sectioning",
                specimen_id=subject_id,
                start_date=sectioning_date,
                end_date=sectioning_date,
                experimenters=_SECTIONING_EXPERIMENTERS,
                procedure_details=[_barseq_lc(subject_id, cfg)],
                notes=f"BARseq LC sections 1-{cfg['barseq_count']} ({_BARSEQ_THICKNESS_UM}um thick)",
            ),
            SpecimenProcedure(
                procedure_type="Sectioning",
                specimen_id=subject_id,
                start_date=sectioning_date,
                end_date=sectioning_date,
                experimenters=_SECTIONING_EXPERIMENTERS,
                procedure_details=[_mapseq_second_batch(subject_id, cfg)],
                notes=f"MAPseq second batch: sections {n_first + 1}-{n_first + n_second} ({_MAPSEQ_THICKNESS_UM}um thick, partial slices)",
            ),
            SpecimenProcedure(
                procedure_type="Sectioning",
                specimen_id=subject_id,
                start_date=sectioning_date,
                end_date=sectioning_date,
                experimenters=_SECTIONING_EXPERIMENTERS,
                procedure_details=[_spinal(subject_id, cfg)],
                notes="MAPseq spinal cord sections, size is approximate",
            ),
            *_generate_mapseq_slide_chunks(subject_id, sectioning_date),
        ],
    )


# ---------------------------------------------------------------------------
# Specimen-id collection (consumed by acquisition_generator)
# ---------------------------------------------------------------------------
def _collect_specimen_ids(
    procedures: Procedures,
    *,
    type_predicate,
    pattern: re.Pattern,
) -> List[str]:
    """Walk a Procedures object and collect output_specimen_ids matching a filter.

    Args:
        procedures: Procedures model to scan.
        type_predicate: Callable(procedure_detail) -> bool; controls which detail
            types are included (e.g. strict `type(d) is Sectioning`).
        pattern: Compiled regex; only IDs that match are kept.

    Returns:
        Deduplicated list of `output_specimen_id` strings, in traversal order.
    """
    ids: List[str] = []
    seen: set = set()
    for sp in procedures.specimen_procedures:
        for detail in sp.procedure_details:
            if not type_predicate(detail):
                continue
            for sec in detail.sections:
                sid = sec.output_specimen_id
                if sid in seen:
                    continue
                if not pattern.search(sid):
                    continue
                seen.add(sid)
                ids.append(sid)
    return ids


def mapseq_specimen_ids(procedures: Procedures) -> List[str]:
    """MAPseq acquisition specimen_id list — everything shipped to CSHL for sequencing.

    Includes the brain-region chunks (e.g. `780345_map001_001`) and the spinal
    cord (e.g. `780345_spinal`). Filters strictly by `type(detail) is Sectioning`
    (not the PlanarSectioning subclass) so the upstream slide IDs
    (e.g. `780345_map001`) are excluded.

    Args:
        procedures: Procedures model previously built by `build_procedures`.

    Returns:
        Deduplicated, ordered list of `output_specimen_id` strings to use as
        the MAPseq Acquisition's `specimen_id`.
    """
    return _collect_specimen_ids(
        procedures,
        type_predicate=lambda d: type(d) is Sectioning,
        pattern=_MAPSEQ_OUTPUT_PATTERN,
    )


def barseq_specimen_ids(procedures: Procedures) -> List[str]:
    """BARseq acquisition specimen_id list — the LC slides imaged in-house.

    Pulls section-level IDs (e.g. `780345_bar001`) from the BARseq LC
    PlanarSectioning sub-procedure.

    Args:
        procedures: Procedures model previously built by `build_procedures`.

    Returns:
        Deduplicated, ordered list of `output_specimen_id` strings to use as
        the BARseq Acquisition's `specimen_id`.
    """
    return _collect_specimen_ids(
        procedures,
        type_predicate=lambda d: isinstance(d, PlanarSectioning),
        pattern=_BAR_PATTERN,
    )
