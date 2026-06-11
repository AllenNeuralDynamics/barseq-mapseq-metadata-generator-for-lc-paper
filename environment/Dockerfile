ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:23.1.0-4-python3.10.12-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG GIT_ASKPASS
COPY git-ask-pass /

# Pin both AIND packages to released versions so the Code Ocean environment
# is fully reproducible. aind-data-schema is what the capsule (run_capsule.py)
# uses at run time; aind-metadata-mapper is only used by the one-off
# prefetch_inputs.py step, but we pin it here too so the whole environment
# is captured.
RUN pip install -U --no-cache-dir \
    aind-data-schema==2.8.1 \
    aind-metadata-mapper==1.3.0
