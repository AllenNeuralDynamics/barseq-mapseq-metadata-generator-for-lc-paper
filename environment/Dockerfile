ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:23.1.0-4-python3.10.12-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ASKPASS
COPY git-askpass /

# aind-data-schema is pinned to the `dev` branch because PR #1781
# (Barseq blackbox acquisition) is merged there but not yet in a release.
# Before publishing this capsule as a release, freeze this to a specific
# commit hash for reproducibility, e.g.:
#   git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@<sha>
RUN pip install -U --no-cache-dir \
    git+https://github.com/AllenNeuralDynamics/aind-data-schema.git@dev
