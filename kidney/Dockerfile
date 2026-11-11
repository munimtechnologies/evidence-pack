# Copyright 2026 Munim, Inc. (MV2). Licensed under the Apache License, Version 2.0 (Apache-2.0).
# One-command container for MV2's open kidney pipeline (kidney/pipeline.py): a folder of .svs whole-slide images in,
# slide QC + glomerulus tables (non-globally-sclerotic / globally sclerotic) out. CPU only.
# Made with AI agents (Claude) working in MV2's name. Research code, not a medical device, not for diagnosis.
#
# Build from the repository root:
#   docker build -f kidney/Dockerfile -t mv2-kidney .
# Run (the 3-class checkpoint from `python -m kidney.gsdet train` is mounted read-only; it is not in this image):
#   docker run --rm -v /path/to/svs:/input:ro -v /path/to/out:/output -v /path/to/gs.pth:/models/gs.pth:ro mv2-kidney
#
# Package versions are the ones the graded stage 5 compute job ran with (its pip freeze).
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.2.2 torchvision==0.17.2 \
 && pip install "numpy==1.26.4" "opencv-python-headless==4.10.0.84" "segmentation-models-pytorch==0.3.3" \
        "timm==0.9.2" "efficientnet_pytorch==0.7.1" "pretrainedmodels==0.7.4" "tifffile==2025.5.10" \
        "imagecodecs==2025.3.30"

WORKDIR /app
COPY kidney/__init__.py kidney/wsi_qc.py kidney/glom.py kidney/gsdet.py kidney/pipeline.py kidney/test_pipeline.py /app/kidney/
COPY LICENSE /app/LICENSE

# The offline tests (including an end-to-end run on a synthetic slide with random weights) can be run with:
#   docker run --rm --entrypoint python mv2-kidney -m unittest -v kidney.test_pipeline
ENTRYPOINT ["python", "-m", "kidney.pipeline"]
CMD ["--in-dir", "/input", "--out-dir", "/output", "--model", "/models/gs.pth"]
