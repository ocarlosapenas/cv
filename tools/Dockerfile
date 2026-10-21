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
ARG GITLEAKS_VERSION
ARG GITLEAKS_SHA256_AMD64
ARG GITLEAKS_SHA256_ARM64
ARG ACTIONLINT_VERSION
ARG ACTIONLINT_SHA256_AMD64
ARG ACTIONLINT_SHA256_ARM64
ARG ZIZMOR_VERSION
ARG ZIZMOR_SHA256_AMD64
ARG ZIZMOR_SHA256_ARM64
ARG LYCHEE_VERSION
ARG LYCHEE_SHA256_AMD64
ARG LYCHEE_SHA256_ARM64
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

# Lint, scan and link tools: same pattern, one verified tarball per tool.
RUN set -eux; \
    fetch() { \
      curl -fsSLo "/tmp/$1.tar.gz" "$2"; \
      echo "$3  /tmp/$1.tar.gz" | sha256sum -c -; \
      mkdir -p "/tmp/$1"; tar -xzf "/tmp/$1.tar.gz" -C "/tmp/$1"; \
      install -m 0755 "$(find "/tmp/$1" -type f -name "$1" | head -n 1)" "/usr/local/bin/$1"; \
    }; \
    case "${TARGETARCH:-amd64}" in \
      amd64) gl=x64;   al=amd64; rs=x86_64; \
             gl_sha="${GITLEAKS_SHA256_AMD64}"; al_sha="${ACTIONLINT_SHA256_AMD64}"; \
             zz_sha="${ZIZMOR_SHA256_AMD64}";   ly_sha="${LYCHEE_SHA256_AMD64}" ;; \
      arm64) gl=arm64; al=arm64; rs=aarch64; \
             gl_sha="${GITLEAKS_SHA256_ARM64}"; al_sha="${ACTIONLINT_SHA256_ARM64}"; \
             zz_sha="${ZIZMOR_SHA256_ARM64}";   ly_sha="${LYCHEE_SHA256_ARM64}" ;; \
      *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    gh=https://github.com; \
    fetch gitleaks "$gh/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${gl}.tar.gz" "$gl_sha"; \
    fetch actionlint "$gh/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_${al}.tar.gz" "$al_sha"; \
    fetch zizmor "$gh/zizmorcore/zizmor/releases/download/v${ZIZMOR_VERSION}/zizmor-${rs}-unknown-linux-gnu.tar.gz" "$zz_sha"; \
    fetch lychee "$gh/lycheeverse/lychee/releases/download/lychee-v${LYCHEE_VERSION}/lychee-${rs}-unknown-linux-gnu.tar.gz" "$ly_sha"

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# poppler-utils: pdfinfo, pdffonts, pdftotext, pdftoppm for the PDF checks.
# python3 libraries come from Debian rather than PyPI: signed, long past the 2-day
# window, and no pip in the image at all. python3-pil draws the visual PR diff.
# git: history scan and gitleaks; codespell: spelling; shellcheck: used by actionlint
# for the run: scripts in workflows.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       poppler-utils python3 python3-yaml python3-jsonschema python3-pytest python3-pil \
       git codespell shellcheck \
    && rm -rf /var/lib/apt/lists/*

COPY --from=fetch /usr/local/bin/typst /usr/local/bin/gitleaks /usr/local/bin/actionlint \
     /usr/local/bin/zizmor /usr/local/bin/lychee /usr/local/bin/
RUN typst --version && pdftotext -v 2>&1 | head -1 && python3 -c "import yaml, jsonschema, pytest, PIL" \
    && gitleaks version && actionlint -version | head -1 && zizmor --version && lychee --version \
    && codespell --version && shellcheck --version | sed -n 2p && git --version

WORKDIR /work
