# Every tool runs inside the pinned cvkit image through tools/run (see tools/).
# Build the image once with: tools/build.sh

VARIANTS := backend ai fde
VERSION ?= dev
RUN := tools/run
TYPST_FLAGS := --root . --ignore-system-fonts --pdf-standard ua-1
DENYLIST := private/denylist.local
PRIVATE := private/contact.private.yaml
# In CI (GitHub sets CI=true) the deny-list comes from a secret and must be present.
DENYLIST_FLAGS := $(if $(CI),--require-denylist)
# Variants published in each release (constant name + dated copy).
RELEASE_VARIANTS ?= backend ai fde

TODAY ?= $(shell date +%Y-%m)
# Private self-reported sources (never committed): LinkedIn screening answers and old
# platform profiles. When present, `make skills` compares them with the evidence.
SCREENING := $(wildcard private/linkedin/*/screening-*.csv)
SELF_REPORTED := $(wildcard private/drafts/*-skills-*.yaml)
SKILLS_CONFIG := --config skills.yaml $(if $(wildcard private/skills-private.yaml),--config private/skills-private.yaml)

# Most recent LinkedIn data export copied into private/linkedin/<date>/ (if any).
LINKEDIN_EXPORT := $(lastword $(sort $(wildcard private/linkedin/*/Positions.csv)))

.PHONY: build test check private clean skills match linkedin release-gate release-assets lint hooks

## build: render every variant to build/<variant>/{resolved.json,cv.pdf,resume.json}
build:
	@for v in $(VARIANTS); do \
	  $(RUN) python3 scripts/resolve.py cv.yaml --variant $$v --version $(VERSION) --out build/$$v/resolved.json \
	  && $(RUN) typst compile $(TYPST_FLAGS) --input data=/build/$$v/resolved.json template/cv.typ build/$$v/cv.pdf \
	  && $(RUN) python3 scripts/export_jsonresume.py build/$$v/resolved.json build/$$v/resume.json \
	  || exit 1; \
	  echo "built build/$$v"; \
	done

## test: unit tests for the scripts
test:
	$(RUN) python3 -m pytest -q -p no:cacheprovider tests

## check: tests, a fresh build, then PDF and confidentiality checks on every variant
check: test build
	@for v in $(VARIANTS); do \
	  $(RUN) pdftotext -q -enc UTF-8 build/$$v/cv.pdf build/$$v/cv.txt \
	  && $(RUN) python3 scripts/check_pdf.py build/$$v/resolved.json build/$$v/cv.pdf \
	  && $(RUN) python3 scripts/check_denylist.py --public $(DENYLIST_FLAGS) --denylist $(DENYLIST) --private $(PRIVATE) \
	       cv.yaml build/$$v/resolved.json build/$$v/resume.json build/$$v/cv.txt \
	  || exit 1; \
	done
	@echo "check: all variants passed"

## release-gate: fail if VERSION is not CalVer or any claim in cv.yaml is pending verification
release-gate:
	$(RUN) python3 scripts/release_gate.py cv.yaml --version $(VERSION)

## release-assets: copy the built PDFs to build/release/ under their release names, then verify them
release-assets:
	rm -rf build/release
	$(RUN) python3 scripts/release_assets.py --copy build --out build/release --tag $(VERSION) --variants "$(RELEASE_VARIANTS)"
	$(RUN) python3 scripts/release_assets.py --verify build/release --tag $(VERSION) --variants "$(RELEASE_VARIANTS)"

## lint: secrets in the whole history, spelling, and workflow lint (the same as CI)
lint:
	$(RUN) gitleaks git --redact --no-banner --log-opts=--all .
	$(RUN) sh -c 'git ls-files -z | xargs -0 codespell'
	@if [ -d .github/workflows ]; then \
	  $(RUN) actionlint && $(RUN) zizmor --offline .github/workflows; \
	fi

## hooks: enable the git hooks in .githooks/ (commit rule, secrets, deny-list, spelling)
hooks:
	git config core.hooksPath .githooks
	@echo "core.hooksPath = $$(git config --get core.hooksPath)"

## private: build PDFs with private contact data into build/private/ (never published)
private:
	@test -f $(PRIVATE) || { echo "missing $(PRIVATE) (see contact.private.example.yaml)"; exit 1; }
	@for v in $(VARIANTS); do \
	  $(RUN) python3 scripts/resolve.py cv.yaml --variant $$v --version $(VERSION) --private $(PRIVATE) --out build/private/$$v/resolved.json \
	  && $(RUN) typst compile $(TYPST_FLAGS) --input data=/build/private/$$v/resolved.json template/cv.typ build/private/$$v/cv.pdf \
	  && $(RUN) python3 scripts/check_pdf.py build/private/$$v/resolved.json build/private/$$v/cv.pdf \
	  && $(RUN) pdftotext -q -enc UTF-8 build/private/$$v/cv.pdf build/private/$$v/cv.txt \
	  && $(RUN) python3 scripts/check_denylist.py --denylist $(DENYLIST) build/private/$$v/cv.txt \
	  || exit 1; \
	  echo "built build/private/$$v"; \
	done

## skills: years per skill computed from the evidence in cv.yaml -> build/skills.{json,md}
skills:
	$(RUN) python3 scripts/skills.py cv.yaml $(SKILLS_CONFIG) --today $(TODAY) \
	  --json build/skills.json --md build/skills.md \
	  $(foreach f,$(SCREENING),--claims-csv $(f)) $(foreach f,$(SELF_REPORTED),--self-reported $(f))

## match: compare a job description with the evidence (JOB=private/jobs/<file>.txt)
match: skills
	@test -n "$(JOB)" || { echo "usage: make match JOB=private/jobs/<file>.txt"; exit 1; }
	$(RUN) python3 scripts/match_job.py --report build/skills.json $(SKILLS_CONFIG) $(JOB)

## linkedin: paste-ready LinkedIn texts with limit checks (+ checklist if an export exists)
linkedin:
	$(RUN) python3 scripts/resolve.py cv.yaml --variant linkedin --out build/linkedin/resolved.json
	$(if $(LINKEDIN_EXPORT),$(RUN) python3 scripts/linkedin_import.py $(dir $(LINKEDIN_EXPORT)) --out build/linkedin/current.yaml)
	$(RUN) python3 scripts/linkedin_texts.py build/linkedin/resolved.json $(SKILLS_CONFIG) \
	  $(if $(LINKEDIN_EXPORT),--current build/linkedin/current.yaml) --out build/linkedin

clean:
	rm -rf build
