"""Per-subject configuration for the LC paper black-box metadata.

Each entry captures the values that vary across subjects: section counts,
acquisition timeframes, and experimenters. Constants that are shared across
subjects (e.g. slice thicknesses, region origins, protocol URLs) live in
generators.py.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

# MAPseq times use noon LA time to avoid timezone-edge day shifts when
# serialized to UTC.
LA_TZ = ZoneInfo("America/Los_Angeles")

SUBJECTS = {
    "780345": {
        "mapseq_first_batch_count": 27,
        "mapseq_second_batch_count": 12,
        "barseq_count": 44,
        "spinal_section_count": 3,  # one specimen, sectioned into 3 thirds
        "sectioning_date": date(2025, 2, 19),
        "mapseq_experimenters": ["Cold Spring Harbor Laboratory (CSHL) MAPseq team"],
        "mapseq_start": datetime(2025, 3, 24, 12, 0, 0, tzinfo=LA_TZ),
        "mapseq_end": datetime(2025, 10, 30, 12, 0, 0, tzinfo=LA_TZ),
        "barseq_experimenters": ["BARseq team"],
        "barseq_start": datetime(2025, 2, 24, 0, 0, 0, tzinfo=LA_TZ),
        "barseq_end": datetime(2025, 3, 21, 23, 59, 59, tzinfo=LA_TZ),
    },
    "780346": {
        "mapseq_first_batch_count": 30,
        "mapseq_second_batch_count": 9,
        "barseq_count": 51,
        "spinal_section_count": 1,
        "sectioning_date": date(2025, 6, 11),
        "mapseq_experimenters": ["Cold Spring Harbor Laboratory (CSHL) MAPseq team"],
        "mapseq_start": datetime(2025, 7, 23, 12, 0, 0, tzinfo=LA_TZ),
        "mapseq_end": datetime(2025, 10, 30, 12, 0, 0, tzinfo=LA_TZ),
        "barseq_experimenters": ["BARseq team"],
        "barseq_start": datetime(2025, 6, 13, 16, 39, 31, tzinfo=LA_TZ),
        "barseq_end": datetime(2025, 7, 11, 23, 59, 59, tzinfo=LA_TZ),
    },
}
