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

Running the capsule writes these files to `/results/`:

```
results/
├── 780345/
│   ├── mapseq/
│   │   ├── procedures.json           # sectioning (locally built) + injections (from service)
│   │   ├── acquisition.json          # MAPseq acquisition (chunk-level specimen IDs)
│   │   ├── subject.json              # broadcast — modality-independent
│   │   └── data_description.json     # MAPseq data description
│   └── barseq/
│       ├── procedures.json           # identical copy of the procedures above
│       ├── acquisition.json          # BARseq acquisition (section-level specimen IDs)
│       ├── subject.json              # identical copy of the subject above
│       └── data_description.json     # BARseq data description
└── 780346/
    └── (same shape)
```

After this capsule runs, each modality folder is a self-contained, ready-
to-upload bundle of all four metadata files DocDB needs.

`procedures.json` is **identical** between the `mapseq/` and `barseq/`
folders for a given subject — the brain was sectioned once and both
modalities used the same slides. It covers MAPseq batches (300 µm partial
slices, plates 0–98 and 112–132), BARseq LC sections (20 µm uniform, plates
99–112), the spinal cord, the per-slide MAPseq chunking, and the upstream
brain injections (merged in from the metadata service's procedures
endpoint, since this capsule does not generate injection metadata).
`subject.json` is also identical between the two folders.

The two `acquisition.json` files are modality-specific and have different
specimen-id semantics:

* **MAPseq** acquisition `specimen_id` is a flat list of everything sent to
  Cold Spring Harbor Laboratory for sequencing: the brain-region chunks
  extracted from each slide (e.g. `780345_map001_001`) plus the spinal cord
  (e.g. `780345_spinal`). All of these are outputs of `Sectioning`
  sub-procedures inside the `Procedures` object.
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

### Step 2: run the capsule

#### On Code Ocean (the canonical release path)

Click **Reproducible Run**. Output lands in `/results/`. After this
finishes, the four metadata files for each (subject × modality) are ready
to hand off for upload to S3 / DocDB.

#### Locally (for development or sanity checks)

```bash
cd code
CO_RESULTS_DIR=../local_results uv run --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev python run_capsule.py
```

(`CO_RESULTS_DIR` overrides the default `/results/` path.)

## Project layout

```
code/
├── run                          # bash entry, called by Code Ocean Reproducible Run
├── run_capsule.py               # orchestrator: iterates SUBJECTS, calls generators, writes JSONs
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
