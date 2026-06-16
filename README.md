# barseq-mapseq-metadata-generator-for-lc-paper

A Code Ocean capsule that generates AIND-data-schema metadata JSON files
(`procedures.json` and `acquisition.json`, one pair per modality) for the
two subjects in the LC paper: **780345** and **780346**.

This capsule exists primarily for **provenance**. The generated JSONs end up
on S3 attached to the BARseq and MAPseq data assets in DocDB. Each bundle
includes a `processing.json` that records the Code Ocean release (web URL +
version) that produced it — looked up at run time from the Code Ocean API —
so a future reader can reproduce the exact bundle by rerunning that release.

## Overview

The capsule produces **one data asset per (subject × modality) combo** — four
in total. A single Reproducible Run (no parameters) writes all four in one
pass, each into its own `/results/<name>/` folder named by the bundle's
`data_description` name. Save each folder out as its own data asset under that
name.

```
results/
├── 780345_2025-03-24_12-00-00/    # 780345 MAPseq
│   ├── procedures.json            # sectioning (locally built) + injections (from service)
│   ├── acquisition.json           # modality-specific
│   ├── subject.json               # passthrough from the metadata service
│   ├── data_description.json      # name field = the folder name = canonical asset name
│   ├── processing.json            # provenance: Code Ocean release URL + version
│   └── MAPseq/                    # raw data, copied verbatim from /data/<asset>/MAPseq/
├── 780345_2025-02-24_12-00-00/    # 780345 BARseq
├── 780346_2025-07-23_12-00-00/    # 780346 MAPseq
└── 780346_2025-06-13_12-00-00/    # 780346 BARseq
```

The four folder names are the canonical AIND names `<subject>_<acquisition_start>`:

| Subject | Modality | Folder / asset name              |
|---------|----------|----------------------------------|
| 780345  | MAPseq   | `780345_2025-03-24_12-00-00`     |
| 780345  | BARseq   | `780345_2025-02-24_12-00-00`     |
| 780346  | MAPseq   | `780346_2025-07-23_12-00-00`     |
| 780346  | BARseq   | `780346_2025-06-13_12-00-00`     |

`procedures.json` is identical across both modalities of a given subject —
the brain was sectioned once and both modalities used the same slides. It
covers MAPseq batches (300 µm partial slices, plates 0–98 and 112–132),
BARseq LC sections (20 µm uniform, plates 99–112), the spinal cord, the
per-slide MAPseq chunking, and the upstream brain injections (merged in
from the metadata service's procedures endpoint).

The two `acquisition.json` flavors have different specimen-id semantics:

* **MAPseq** acquisition `specimen_id` is a flat list of everything sent to
  Cold Spring Harbor Laboratory for sequencing: the brain-region chunks
  extracted from each slide (e.g. `780345_map001_001`) plus the spinal cord
  (e.g. `780345_spinal`). All are outputs of `Sectioning` sub-procedures
  inside the `Procedures` object.
* **BARseq** acquisition `specimen_id` is a flat list of the LC section
  outputs from the `PlanarSectioning` sub-procedure (e.g. `780345_bar001`).
  These are the slides imaged in-house at the Allen Institute.

Both lists are derived directly from the `Procedures` object built in the
same run, so the acquisition and procedures stay in sync by construction.

## Supplemental files folded into the raw bundles

A handful of per-subject files belong in the raw assets but currently live in
separate "loose CSV" data assets rather than inside the `780345_*` / `780346_*`
input assets. `run_capsule.py` folds them back into each subject's
`<Modality>/` folder so they travel downstream: the MAT2RDS conversion capsule
and the BARseq/MAPseq analysis capsule read them from `<asset>/<Modality>/`,
and the analysis breaks without them (the BARseq–MAPseq barcode-matching stage
dies on the missing reads).

| Supplemental asset (mount name) | Folded into | Example files |
|---------------------------------|-------------|---------------|
| `BARseq_soma_barcodes`          | `BARseq/`   | `barcodes_BC_qc_<id>.csv`, `LC_visualQC_barcoded_cells_<id>.csv` |
| `MAPseq_ROI_info`               | `MAPseq/`   | per-subject MAPseq ROI info |

Files are routed to the right subject by `<subject_id>` in the filename
(`SUPPLEMENTAL_ASSETS` in `run_capsule.py`). Attach both assets in Code Ocean
under exactly those mount names; if one isn't mounted the run warns and skips
it rather than failing.

Background: the raw assets were rebuilt without these files
(AllenNeuralDynamics/aind-scientific-computing#747), which silently broke the
combined MAPseq analysis downstream. Baking them into the raw bundle here fixes
it at the source, so every future rebuild carries them through.

## Running

The capsule has two pieces. **Step 1** pre-populates the metadata-service
files into `code/inputs/` and was performed once when this capsule was
built; the resulting files are committed to the repo. **Step 2** is the
capsule itself — the part that actually runs on Code Ocean — and combines
the prefetched inputs with locally-built procedures and acquisitions to
produce the final bundle. This is a provenance artifact: nobody is
expected to rerun the generation in the future, the published Code Ocean
release is the record.

### Step 1: prefetch metadata inputs (already done)

`subject.json`, `data_description.json`, and the upstream
`procedures.json` (which carries the brain injections) come from the AIND
on-prem metadata service. They can't be fetched from inside the capsule
(no network access to on-prem), so `code/prefetch_inputs.py` was run once
locally to populate `code/inputs/<subject>/`, and those files are
committed to the repo.

You should not need to run this again — these subjects are frozen and
the capsule has everything it needs to reproduce the metadata bundle from
the committed inputs. The script is preserved here for transparency about
where each prefetched file came from. The (unlikely) cases that would
warrant a re-run: an upstream correction to a subject record, a project
metadata change that needs to be reflected in `data_description.json`, or
adding a new subject to `subjects.py`. To re-run on-prem:

```bash
cd code
uv run \
  --with aind-data-schema==2.8.1 \
  --with aind-metadata-mapper==1.3.0 \
  python prefetch_inputs.py
```

`PROJECT_NAME` lives at the top of `prefetch_inputs.py` and must match a
project name registered in the metadata service exactly, otherwise
`funding_source` and `investigators` come back empty in the resulting
`data_description.json`.

### Step 2: run the capsule (once)

#### On Code Ocean (the canonical release path)

Attach the two `780345_*` / `780346_*` input data assets (which contain the
`BARseq/` and `MAPseq/` subfolders) **and** the two supplemental loose-CSV
assets `BARseq_soma_barcodes` and `MAPseq_ROI_info` (mounted under exactly
those names — see "Supplemental files folded into the raw bundles" above).
Then click **Reproducible Run** — no parameters. The single run writes all four bundles into
`/results/<name>/` folders (see the layout above). Save each folder out as
its own data asset under its folder name, then hand the four asset references
off to whoever owns moving them to `aind-open-data`.

#### Locally (for development or sanity checks)

```bash
cd code
CO_RESULTS_DIR=../local_results uv run --with aind-data-schema==2.8.1 \
    python run_capsule.py
```

This writes all four bundles under `CO_RESULTS_DIR`. The capsule warns and
skips the raw-data copy for any subject whose `/data/<subject>_*` asset isn't
mounted, so local runs (without input assets) still produce valid metadata
bundles — just without the raw data alongside.

## Project layout

```
code/
├── run                          # bash entry, called by Code Ocean Reproducible Run
├── run_capsule.py               # entry point — writes all four bundles to /results/<name>/ in one pass
├── subjects.py                  # SUBJECTS dict — edit to add or change a subject
├── procedures_generator.py      # build_procedures + slide-region chunking + specimen-id collectors
├── acquisition_generator.py     # build_acquisition + per-modality config (notes, protocol IDs, modality enum)
├── provenance.py                # fetch Code Ocean release URL + version, write processing.json
├── _procedures_helpers.py       # generic sectioning utilities (verbatim copy from PR #1763)
├── prefetch_inputs.py           # run locally to refresh inputs/ from the metadata service
└── inputs/                      # committed: subject + procedures + per-modality data_description per subject
    ├── 780345/
    │   ├── subject.json
    │   ├── procedures_from_service.json
    │   ├── mapseq/data_description.json
    │   └── barseq/data_description.json
    └── 780346/...
environment/
└── Dockerfile                   # pins aind-data-schema + aind-metadata-mapper to released versions
```

### Where to edit what

| Thing you want to change                                     | File                                |
|--------------------------------------------------------------|-------------------------------------|
| Add a new subject, change dates / counts                     | `code/subjects.py`                  |
| Tweak procedure notes, sectioning constants, slide regions   | `code/procedures_generator.py`      |
| Tweak acquisition notes, protocol IDs                        | `code/acquisition_generator.py`     |
| Change `PROJECT_NAME` or per-modality `data_summary`         | `code/prefetch_inputs.py`           |
| Change `processing.json` experimenters                       | `code/provenance.py`                |
| Refresh subject / data_description / injection procedures    | re-run `code/prefetch_inputs.py`    |
| Change pinned `aind-data-schema` / `aind-metadata-mapper`    | `environment/Dockerfile`            |

## Provenance: `processing.json`

Each bundle gets a `processing.json` (an AIND-data-schema `Processing` record)
whose `code.url` and `code.version` point at the exact Code Ocean release that
produced it. `provenance.py` looks these up **at run time** from the
Code Ocean REST API, so nothing has to be hardcoded before cutting a release —
there's no chicken-and-egg "set the URL, then cut a new release" dance.

This requires the **Code Ocean API Credentials** Secret to be attached to the
capsule (Capsule Settings → Credentials). That exposes `API_KEY` at run time;
combined with the `CO_CAPSULE_ID` / `CO_COMPUTATION_ID` env vars Code Ocean
injects into every Reproducible Run, `provenance.py` calls
`/api/v1/capsules/<id>` and `/api/v1/computations/<id>` to read the capsule
slug (→ web URL) and the release version. On a local run (no credentials)
`processing.json` is skipped with a warning rather than written with
placeholder provenance.

Workflow:

1. Develop here, validate the JSONs locally.
2. Push to a Code Ocean capsule and attach the **Code Ocean API Credentials**
   Secret. Run **Reproducible Run** to confirm.
3. Cut a release of the capsule.
4. Run the capsule from that release. Each of the four bundles gets a
   `processing.json` stamped with that release's URL + version.
5. Upload the resulting bundles alongside the data assets on S3 / DocDB.

`EXPERIMENTERS` at the top of `provenance.py` records who published the release
in `processing.json`; edit it if that's not you.
