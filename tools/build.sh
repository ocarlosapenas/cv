#!/usr/bin/env bash
# Build the pinned cvkit image from tools/Dockerfile and the pins in tools/tools.env.
# The image is labelled with a hash of both files; tools/run refuses to use an image
# whose label does not match, so a changed pin can never run on a stale toolchain.
set -euo pipefail
cd "$(dirname "$0")"

# shellcheck source=tools.env
. ./tools.env

IMAGE="cv/cvkit:pinned"
HASH="$(cat Dockerfile tools.env | shasum -a 256 | cut -d' ' -f1)"

docker build \
  --build-arg BASE_IMAGE="$BASE_IMAGE" \
  --build-arg TYPST_VERSION="$TYPST_VERSION" \
  --build-arg TYPST_SHA256_AMD64="$TYPST_SHA256_AMD64" \
  --build-arg TYPST_SHA256_ARM64="$TYPST_SHA256_ARM64" \
  --build-arg GITLEAKS_VERSION="$GITLEAKS_VERSION" \
  --build-arg GITLEAKS_SHA256_AMD64="$GITLEAKS_SHA256_AMD64" \
  --build-arg GITLEAKS_SHA256_ARM64="$GITLEAKS_SHA256_ARM64" \
  --build-arg ACTIONLINT_VERSION="$ACTIONLINT_VERSION" \
  --build-arg ACTIONLINT_SHA256_AMD64="$ACTIONLINT_SHA256_AMD64" \
  --build-arg ACTIONLINT_SHA256_ARM64="$ACTIONLINT_SHA256_ARM64" \
  --build-arg ZIZMOR_VERSION="$ZIZMOR_VERSION" \
  --build-arg ZIZMOR_SHA256_AMD64="$ZIZMOR_SHA256_AMD64" \
  --build-arg ZIZMOR_SHA256_ARM64="$ZIZMOR_SHA256_ARM64" \
  --build-arg LYCHEE_VERSION="$LYCHEE_VERSION" \
  --build-arg LYCHEE_SHA256_AMD64="$LYCHEE_SHA256_AMD64" \
  --build-arg LYCHEE_SHA256_ARM64="$LYCHEE_SHA256_ARM64" \
  --label "cv.toolchain.hash=$HASH" \
  -t "$IMAGE" .

echo "Built $IMAGE (Typst $TYPST_VERSION, toolchain hash ${HASH:0:12})"
