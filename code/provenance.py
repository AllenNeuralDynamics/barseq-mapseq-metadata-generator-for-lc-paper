"""Code Ocean provenance for the generated metadata bundle.

run_capsule.py writes a `processing.json` describing the run. The capsule's
release version and web URL are looked up at run time from the Code Ocean REST
API, so nothing has to be hardcoded before cutting a release (and there's no
chicken-and-egg release dance).

Requires the "Code Ocean API Credentials" Secret to be attached to the capsule
(Capsule Settings -> Credentials), which exposes `API_KEY` at run time, along
with the `CO_CAPSULE_ID` / `CO_COMPUTATION_ID` env vars Code Ocean injects into
every Reproducible Run. On a local run (no credentials) processing.json is
skipped rather than written with placeholder provenance.
"""

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from aind_data_schema.components.identifiers import Code
from aind_data_schema.core.processing import DataProcess, ProcessStage, Processing
from aind_data_schema_models.process_names import ProcessName

CO_API_BASE = "https://codeocean.allenneuraldynamics.org/api/v1"
CO_WEB_BASE = "https://codeocean.allenneuraldynamics.org/capsule"

# Recorded as the DataProcess experimenters in processing.json — i.e. who ran
# this capsule to publish the release. Edit if someone else publishes it.
EXPERIMENTERS = ["Polina Kosillo"]


def fetch_co_provenance() -> tuple[str, str]:
    """Return (capsule_url, version) for the running Code Ocean capsule.

    Calls the Code Ocean REST API at run time to look up the capsule's web URL
    (built from the slug) and the release version of this run. ``version`` is
    ``"from non-release editable capsule"`` when running an editable
    (non-release) capsule; otherwise it's a string like ``"v3.0"``.

    Requires the "Code Ocean API Credentials" Secret attached to the capsule,
    which exposes API_KEY at run time. Raises RuntimeError if any required env
    var is missing or the API call fails.
    """
    api_key = os.environ.get("API_KEY")
    capsule_id = os.environ.get("CO_CAPSULE_ID")
    computation_id = os.environ.get("CO_COMPUTATION_ID")
    if not api_key or not capsule_id or not computation_id:
        raise RuntimeError(
            "Missing Code Ocean env vars (API_KEY / CO_CAPSULE_ID / "
            "CO_COMPUTATION_ID). Attach the 'Code Ocean API Credentials' "
            "Secret to the capsule (Capsule Settings -> Credentials)."
        )

    auth = base64.b64encode(f"{api_key}:".encode()).decode()
    headers = {"Authorization": f"Basic {auth}"}

    def _get(path: str) -> dict:
        req = urllib.request.Request(f"{CO_API_BASE}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    try:
        capsule = _get(f"/capsules/{capsule_id}")
        computation = _get(f"/computations/{computation_id}")
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Code Ocean API call failed: {e}") from e

    capsule_url = f"{CO_WEB_BASE}/{capsule['slug']}/tree"
    if "version" in computation:
        version = f"v{computation['version']}.0"
    else:
        version = "from non-release editable capsule"
    return capsule_url, version


def write_processing(results_dir: Path) -> None:
    """Build and write processing.json describing this metadata-generation run.

    Skipped with a warning if the Code Ocean API credentials aren't available
    (e.g. a local run), since the capsule URL + release version can only be
    populated from the runtime API call.
    """
    try:
        capsule_url, version = fetch_co_provenance()
    except RuntimeError as e:
        print(f"  WARNING: skipping processing.json -- {e}")
        return

    code = Code(
        url=capsule_url,
        name="barseq-mapseq-metadata-generator-for-lc-paper",
        version=version,
        run_script=Path("code/run"),
        language="Python",
    )
    process = DataProcess(
        process_type=ProcessName.OTHER,
        name="Metadata generation",
        stage=ProcessStage.PROCESSING,
        code=code,
        experimenters=EXPERIMENTERS,
        start_date_time=datetime.now(timezone.utc),
        notes=(
            "Generated the AIND-data-schema metadata bundle (procedures, "
            "acquisition, subject, data_description) for this raw data asset."
        ),
    )
    processing = Processing(data_processes=[process])
    processing.write_standard_file(output_directory=results_dir)
    print("  wrote processing.json")
