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
    return PlanarSectioning(
        sections=sections,
        section_orientation=section_orientation,
    )
