# check=skip=InvalidDefaultArgInFrom
# (BASE_IMAGE has no default on purpose: the only pin lives in tools/tools.env, so a
# build that bypasses tools/build.sh fails instead of pulling an unpinned image.)
#
# cvkit: every tool this repository needs, baked into one pinned image.
# Rebuild is a conscious act: change tools/tools.env and re-run tools/build.sh.
#
# Typst comes from the upstream GitHub release, verified against a recorded SHA256,
# because a checksum is immutable while a Docker tag can be re-pushed. Everything
# else comes from the Debian archive of a digest-pinned base image.

ARG BASE_IMAGE
FROM ${BASE_IMAGE} AS fetch

ARG TYPST_VERSION
ARG TYPST_SHA256_AMD64
ARG TYPST_SHA256_ARM64
# Provided by BuildKit; selects the matching linux binary.
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      amd64) triple=x86_64-unknown-linux-musl;  sha="${TYPST_SHA256_AMD64}" ;; \
      arm64) triple=aarch64-unknown-linux-musl; sha="${TYPST_SHA256_ARM64}" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    url="https://github.com/typst/typst/releases/download/v${TYPST_VERSION}/typst-${triple}.tar.xz"; \
    curl -fsSLo /tmp/typst.tar.xz "$url"; \
    echo "${sha}  /tmp/typst.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/typst.tar.xz -C /tmp; \
    install -m 0755 "/tmp/typst-${triple}/typst" /usr/local/bin/typst; \
    /usr/local/bin/typst --version

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# poppler-utils: pdfinfo, pdffonts, pdftotext, pdftoppm for the PDF checks.
# python3 libraries come from Debian rather than PyPI: signed, long past the 2-day
# window, and no pip in the image at all.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       poppler-utils python3 python3-yaml python3-jsonschema python3-pytest \
    && rm -rf /var/lib/apt/lists/*

COPY --from=fetch /usr/local/bin/typst /usr/local/bin/typst
RUN typst --version && pdftotext -v 2>&1 | head -1 && python3 -c "import yaml, jsonschema, pytest"

WORKDIR /work
