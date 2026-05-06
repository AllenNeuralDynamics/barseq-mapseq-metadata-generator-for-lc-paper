# barseq-mapseq-metadata-generator-for-lc-paper

A Code Ocean capsule that generates AIND-data-schema metadata JSON files
(`procedures.json` and `acquisition.json`, one pair per modality) for the
two subjects in the LC paper: **780345** and **780346**.

This capsule exists primarily for **provenance**. The generated JSONs end up
on S3 attached to the BARseq and MAPseq data assets in DocDB. Each JSON
includes a `notes` field that points back to a fixed Code Ocean release of
this capsule, so a future reader can reproduce the exact
generated file by rerunning the linked release.

## Overview

The capsule produces **one data asset per (subject × modality) combo**, so
**four runs total** to publish all four assets. Each Reproducible Run
takes `--subject-id` and `--modality` parameters (set via the Code Ocean
App Panel) and writes a single flat `/results/` folder that contains both
the raw data (copied from the attached input asset) and freshly-generated
metadata:

```
results/
├── procedures.json           # sectioning (locally built) + injections (from service)
├── acquisition.json          # modality-specific
├── subject.json              # passthrough from the metadata service
├── data_description.json     # modality-specific (name field = canonical asset name)
└── <Modality>/               # raw data, copied verbatim from /data/<asset>/<Modality>/
```

Each `/results/` folder becomes one Code Ocean data asset with the
canonical AIND name `<modality>_<subject>_<acquisition_start>`:

| Run | --subject-id | --modality | Resulting asset name                          |
|-----|--------------|------------|-----------------------------------------------|
| 1   | 780345       | MAPseq     | `mapseq_780345_2025-03-24_12-00-00`           |
| 2   | 780345       | BARseq     | `barseq_780345_2025-02-24_12-00-00`           |
| 3   | 780346       | MAPseq     | `mapseq_780346_2025-07-23_12-00-00`           |
| 4   | 780346       | BARseq     | `barseq_780346_2025-06-13_12-00-00`           |

The `name` field in each `data_description.json` matches the asset name in
the table above and is what Code Ocean should use when promoting `/results/`
to a data asset.

`procedures.json` is identical across all four runs of a given subject —
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
  --with git+https://github.com/AllenNeuralDynamics/aind-metadata-mapper.git@dev \
  --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev \
  python prefetch_inputs.py
```

`PROJECT_NAME` lives at the top of `prefetch_inputs.py` and must match a
project name registered in the metadata service exactly, otherwise
`funding_source` and `investigators` come back empty in the resulting
`data_description.json`.

### Step 2: run the capsule (four times)

#### On Code Ocean (the canonical release path)

For each row in the table above, attach the input data asset matching the
subject (the `780345_*` or `780346_*` asset that contains the `BARseq/`
and `MAPseq/` subfolders), set the App Panel parameters to that row's
`--subject-id` and `--modality`, and click **Reproducible Run**. Each run
produces a `/results/` folder that Code Ocean turns into a data asset
named per the table.

After all four runs are done, hand the four data asset references off to
whoever owns moving them from the internal Code Ocean bucket to
`aind-open-data`.

#### Locally (for development or sanity checks)

```bash
cd code
CO_RESULTS_DIR=../local_results uv run --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev \
    python run_capsule.py --subject-id 780345 --modality MAPseq
```

Each invocation writes one combo's bundle to `CO_RESULTS_DIR`. Each run
clobbers the previous one, so set `CO_RESULTS_DIR` to a per-combo path if
you want to keep all four locally:

```bash
for combo in "780345 MAPseq" "780345 BARseq" "780346 MAPseq" "780346 BARseq"; do
  read s m <<< "$combo"
  CO_RESULTS_DIR=../local_results/${m,,}_${s} uv run --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev \
      python run_capsule.py --subject-id $s --modality $m
done
```

The capsule warns and skips the raw-data copy if `/data/<subject>_*` isn't
present, so local runs (without the input asset mounted) still produce
valid metadata bundles — just without the raw data alongside.

## Project layout

```
code/
├── run                          # bash entry, called by Code Ocean Reproducible Run
├── run_capsule.py               # entry point — takes --subject-id/--modality, writes one bundle to /results/
├── subjects.py                  # SUBJECTS dict — edit to add or change a subject
├── procedures_generator.py      # build_procedures + slide-region chunking + specimen-id collectors
├── acquisition_generator.py     # build_acquisition + per-modality config (notes, protocol IDs, modality enum)
├── provenance.py                # PROVENANCE_URL + augment_notes (shared by procedures + acquisitions)
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
└── Dockerfile                   # pins aind-data-schema to dev branch
```

### Where to edit what

| Thing you want to change                                     | File                                |
|--------------------------------------------------------------|-------------------------------------|
| Add a new subject, change dates / counts                     | `code/subjects.py`                  |
| Tweak procedure notes, sectioning constants, slide regions   | `code/procedures_generator.py`      |
| Tweak acquisition notes, protocol IDs                        | `code/acquisition_generator.py`     |
| Change `PROJECT_NAME` or per-modality `data_summary`         | `code/prefetch_inputs.py`           |
| Set `PROVENANCE_URL` after a Code Ocean release              | `code/provenance.py`                |
| Refresh subject / data_description / injection procedures    | re-run `code/prefetch_inputs.py`    |
| Change pinned `aind-data-schema` version                     | `environment/Dockerfile`            |

## Provenance: setting `PROVENANCE_URL`

`provenance.py` has a module-level `PROVENANCE_URL` (default `None`). When
this capsule is published as a Code Ocean release, set this to the release
URL — every generated JSON's `notes` field will then carry a line like:

```
Generated by: https://codeocean.allenneuraldynamics.org/capsule/<id>
```

Workflow:

1. Develop here, validate the JSONs locally.
2. Push to a Code Ocean capsule. Run **Reproducible Run** to confirm.
3. Cut a release of the capsule. Copy its URL.
4. Set `PROVENANCE_URL` to that URL.
5. Freeze `aind-data-schema` in the Dockerfile to a specific commit hash.
6. Cut a *new* release. That release's URL is the one that ships in the JSONs.
7. Re-run the capsule from the final release; upload the JSONs alongside the
   data assets on S3 / DocDB.
