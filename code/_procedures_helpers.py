"""Generic sectioning helpers, copied verbatim from aind-data-schema PR #1763
(`examples/procedures_sectioning.py`, branch `1729-barseqmapseq-procedures`,
author: Dan Birman).

Kept here so the capsule is self-contained and independent of the example-
file location in the schema repo. If these helpers are ever promoted into
`aind_data_schema.components.specimen_procedures`, delete this file and
import from there instead.
"""

from typing import List

from aind_data_schema_models.units import SizeUnit

from aind_data_schema.components.coordinates import Translation
from aind_data_schema.components.specimen_procedures import (
    PlanarSection,
    PlanarSectioning,
    SectionOrientation,
)


def create_planar_section(
    specimen_id: str,
    section_id: str,
    coordinate_system_name: str,
    start_um: float,
    thickness: float,
    thickness_unit: SizeUnit,
) -> PlanarSection:
    """Build a single PlanarSection at a given start position.

    Args:
        specimen_id: Subject ID; combined with section_id to form output_specimen_id.
        section_id: Per-section suffix (e.g. "map001"), appended to specimen_id.
        coordinate_system_name: Name of the coordinate system the start position is in.
        start_um: Start position along the sectioning axis, in micrometers.
        thickness: Section thickness in `thickness_unit`.
        thickness_unit: Unit for `thickness` and `start_um`.

    Returns:
        A single PlanarSection model.
    """
    return PlanarSection(
        output_specimen_id=f"{specimen_id}_{section_id}",
        coordinate_system_name=coordinate_system_name,
        start_coordinate=Translation(translation=[round(start_um), 0, 0]),
        thickness=thickness,
        thickness_unit=thickness_unit,
    )


def create_uniform_sections(
    specimen_id: str,
    start_section_num: int,
    num_sections: int,
    start_um: float,
    thickness: float,
    thickness_unit: SizeUnit,
    coordinate_system_name: str = "CCF",
    section_prefix: str = "sec",
) -> List[PlanarSection]:
    """Build a list of evenly-spaced PlanarSections (each at start_um + i*thickness).

    Args:
        specimen_id: Subject ID, used as the prefix for every section's output_specimen_id.
        start_section_num: Number for the first section (1-based, zero-padded to 3 digits).
        num_sections: Number of sections to build.
        start_um: Start position of the first section, in micrometers.
        thickness: Section thickness; also the spacing between consecutive sections.
        thickness_unit: Unit for `thickness` and `start_um`.
        coordinate_system_name: Name of the coordinate system (default "CCF").
        section_prefix: Prefix used in the section ID (default "sec" → "sec001", "sec002", …).

    Returns:
        A list of PlanarSection models, one per section.
    """
    return [
        create_planar_section(
            specimen_id=specimen_id,
            section_id=f"{section_prefix}{start_section_num + i:03d}",
            coordinate_system_name=coordinate_system_name,
            start_um=start_um + i * thickness,
            thickness=thickness,
            thickness_unit=thickness_unit,
        )
        for i in range(num_sections)
    ]


def create_nonuniform_sections(
    specimen_id: str,
    num_sections: int,
    start_positions_um: List[float],
    thickness: float,
    thickness_unit: SizeUnit,
    coordinate_system_name: str = "CCF",
    section_prefix: str = "sec",
    start_section_num: int = 1,
) -> List[PlanarSection]:
    """Build a list of PlanarSections at explicit (non-uniform) start positions.

    Args:
        specimen_id: Subject ID, used as the prefix for every section's output_specimen_id.
        num_sections: Number of sections; must equal len(start_positions_um).
        start_positions_um: Start position of each section, in micrometers.
        thickness: Section thickness (uniform across all sections).
        thickness_unit: Unit for `thickness` and `start_positions_um`.
        coordinate_system_name: Name of the coordinate system (default "CCF").
        section_prefix: Prefix used in the section ID (default "sec").
        start_section_num: Number for the first section (default 1, 1-based, zero-padded).

    Returns:
        A list of PlanarSection models, one per provided start position.

    Raises:
        ValueError: if `num_sections` does not match `len(start_positions_um)`.
    """
    if num_sections != len(start_positions_um):
        raise ValueError("num_sections and start_positions_um must have same length")

    return [
        create_planar_section(
            specimen_id=specimen_id,
            section_id=f"{section_prefix}{start_section_num + i:03d}",
            coordinate_system_name=coordinate_system_name,
            start_um=start_um,
            thickness=thickness,
            thickness_unit=thickness_unit,
        )
        for i, start_um in enumerate(start_positions_um)
    ]


def create_planar_sectioning(
    sections: List[PlanarSection],
    section_orientation: SectionOrientation = SectionOrientation.CORONAL,
) -> PlanarSectioning:
    """Wrap a list of PlanarSections into a PlanarSectioning sub-procedure.

    Args:
        sections: PlanarSection list to embed.
        section_orientation: Anatomical plane of sectioning (default CORONAL).

    Returns:
        A PlanarSectioning model carrying the sections and orientation.
    """
    return PlanarSectioning(
        sections=sections,
        section_orientation=section_orientation,
    )
