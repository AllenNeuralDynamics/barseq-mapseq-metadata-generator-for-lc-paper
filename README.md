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
│   │   ├── procedures.json                  # one Procedures object covering all sectioning
│   │   ├── acquisition.json                 # MAPseq acquisition (chunk-level specimen IDs)
│   │   └── gather_metadata_settings.json    # JobSettings for the local gather_metadata step
│   └── barseq/
│       ├── procedures.json                  # identical copy of the procedures above
│       ├── acquisition.json                 # BARseq acquisition (section-level specimen IDs)
│       └── gather_metadata_settings.json
└── 780346/
    ├── mapseq/
    │   ├── procedures.json
    │   ├── acquisition.json
    │   └── gather_metadata_settings.json
    └── barseq/
        ├── procedures.json
        ├── acquisition.json
        └── gather_metadata_settings.json
```

`procedures.json` is **identical** between the `mapseq/` and `barseq/`
folders for a given subject — the brain was sectioned once and both
modalities used the same slides. The file is repeated so each modality
folder is a self-contained unit ready to upload alongside its data asset.
It covers MAPseq batches (300 µm partial slices, plates 0–98 and 112–132),
BARseq LC sections (20 µm uniform, plates 99–112), the spinal cord, and
the per-slide MAPseq chunking.

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

### Step 1: generate procedures + acquisition + settings (this capsule)

#### On Code Ocean (the way it's meant to run)

Click **Reproducible Run**. Output lands in `/results/`.

#### Locally (for development or sanity checks)

```bash
cd code
CO_RESULTS_DIR=../local_results uv run --with git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev python run_capsule.py
```

(`CO_RESULTS_DIR` overrides the default `/results/` path.)

### Step 2: gather subject + data_description (run locally, on-prem)

`subject.json` and `data_description.json` cannot be produced inside this
capsule because they require calls to the AIND on-prem metadata service
(`http://aind-metadata-service`) for subject info, funding source, and
investigators. After Step 1, run [`aind-metadata-mapper`'s `gather_metadata`
job](https://github.com/AllenNeuralDynamics/aind-metadata-mapper) locally,
once per modality folder, on a machine with network access to the metadata
service. Each invocation reads the `gather_metadata_settings.json` and
existing `acquisition.json` / `procedures.json` from that folder, fetches
the missing pieces, and writes `subject.json` + `data_description.json`
into the same folder.

`project_name` is hardcoded in `code/gather_metadata_settings_generator.py` (`PROJECT_NAME`) and must
match a project name registered in the AIND metadata service exactly,
otherwise `funding_source` and `investigators` come back empty. If the
project gets renamed upstream, update `PROJECT_NAME` and rerun Step 1.

```bash
# Run from each modality folder. Repeat for all four (subject × modality).
cd results/780345/mapseq
uv run --with git+https://github.com/AllenNeuralDynamics/aind-metadata-mapper.git@dev \
    python -m aind_metadata_mapper.gather_metadata \
    --job-settings "$(cat gather_metadata_settings.json)"
```

Or loop over all four:

```bash
for d in results/780345/mapseq results/780345/barseq \
         results/780346/mapseq results/780346/barseq; do
  ( cd "$d" && uv run --with git+https://github.com/AllenNeuralDynamics/aind-metadata-mapper.git@dev \
      python -m aind_metadata_mapper.gather_metadata \
      --job-settings "$(cat gather_metadata_settings.json)" )
done
```

After Step 2, each modality folder contains the full bundle
(`subject.json`, `data_description.json`, `procedures.json`,
`acquisition.json`) ready to hand off for upload to S3 / DocDB.

## Project layout

```
code/
├── run                                       # bash entry, called by Code Ocean Reproducible Run
├── run_capsule.py                            # orchestrator: iterates SUBJECTS, calls generators, writes JSONs
├── subjects.py                               # SUBJECTS dict — edit to add or change a subject
├── procedures_generator.py                   # build_procedures + slide-region chunking + specimen-id collectors
├── acquisition_generator.py                  # build_acquisition + per-modality config (notes, protocol IDs, modality enum)
├── gather_metadata_settings_generator.py     # build_gather_metadata_settings + PROJECT_NAME, data summaries
├── provenance.py                             # PROVENANCE_URL + augment_notes (shared by procedures + acquisitions)
└── _procedures_helpers.py                    # generic sectioning utilities (verbatim copy from PR #1763)
environment/
└── Dockerfile                                # pins aind-data-schema to dev branch
```

### Where to edit what

| Thing you want to change                                     | File                                          |
|--------------------------------------------------------------|-----------------------------------------------|
| Add a new subject, change dates / counts                     | `code/subjects.py`                            |
| Tweak procedure notes, sectioning constants, slide regions   | `code/procedures_generator.py`                |
| Tweak acquisition notes, protocol IDs                        | `code/acquisition_generator.py`               |
| Change `PROJECT_NAME` or per-modality `data_summary`         | `code/gather_metadata_settings_generator.py`  |
| Set `PROVENANCE_URL` after a Code Ocean release              | `code/provenance.py`                          |
| Change pinned `aind-data-schema` version                     | `environment/Dockerfile`                      |

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
