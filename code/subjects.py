"""Per-subject configuration for the LC paper black-box metadata.

Each entry captures the values that vary across subjects: section counts,
acquisition timeframes, and experimenters. Constants that are shared across
subjects (e.g. slice thicknesses, region origins, protocol URLs) live in
generators.py.

Sources
-------
* MAPseq acquisition dates (mailed-to-CSHL → last reprocessing):
    Polina Kosillo Teams chat, 2026-05-01.
* BARseq acquisition dates and experimenters:
    aind-workbench projects/barseq_blackbox_acquisition/barseq_acquisition.py
    (folder dates and experiment_detail.txt under /allen/aind/stage/barseq/).
* Sectioning structure (counts, naming, slide regions):
    aind-data-schema PR #1763 (examples/procedures_sectioning.py,
    branch 1729-barseqmapseq-procedures, author: Dan Birman).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

LA_TZ = ZoneInfo("America/Los_Angeles")

SUBJECTS = {
    "780345": {
        # Sectioning structure
        "mapseq_first_batch_count": 27,
        "mapseq_second_batch_count": 12,
        "barseq_count": 44,
        "spinal_section_count": 3,  # one specimen, sectioned into 3 thirds
        # MAPseq acquisition (mailed to CSHL → last reprocessing)
        # Times set to noon to avoid timezone-edge day shifts.
        "mapseq_experimenters": ["Cold Spring Harbor Laboratory (CSHL) MAPseq team"],
        "mapseq_start": datetime(2025, 3, 24, 12, 0, 0, tzinfo=LA_TZ),
        "mapseq_end": datetime(2025, 10, 30, 12, 0, 0, tzinfo=LA_TZ),
        # BARseq acquisition (in-house imaging)
        # Start: first folder date 20250224_780345_slide4_maxprojection.
        # End: last folder date 20250321_780345_slide1a_maxprojection.
        "barseq_experimenters": ["BARseq team"],
        "barseq_start": datetime(2025, 2, 24, 0, 0, 0, tzinfo=LA_TZ),
        "barseq_end": datetime(2025, 3, 21, 23, 59, 59, tzinfo=LA_TZ),
    },
    "780346": {
        "mapseq_first_batch_count": 30,
        "mapseq_second_batch_count": 9,
        "barseq_count": 51,
        "spinal_section_count": 1,
        "mapseq_experimenters": ["Cold Spring Harbor Laboratory (CSHL) MAPseq team"],
        "mapseq_start": datetime(2025, 7, 23, 12, 0, 0, tzinfo=LA_TZ),
        "mapseq_end": datetime(2025, 10, 30, 12, 0, 0, tzinfo=LA_TZ),
        # BARseq acquisition (in-house imaging)
        # Start: experiment_detail.txt in first slide folder (20250613_780346_slide11_maxprojection).
        # End: last folder date 20250711_780346_slide3_maxprojection.
        "barseq_experimenters": ["BARseq team"],
        "barseq_start": datetime(2025, 6, 13, 16, 39, 31, tzinfo=LA_TZ),
        "barseq_end": datetime(2025, 7, 11, 23, 59, 59, tzinfo=LA_TZ),
    },
}
