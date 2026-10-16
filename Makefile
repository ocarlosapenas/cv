# Every tool runs inside the pinned cvkit image through tools/run (see tools/).
# Build the image once with: tools/build.sh

VARIANTS := backend ai fde
VERSION ?= dev
RUN := tools/run
TYPST_FLAGS := --root . --ignore-system-fonts --pdf-standard ua-1
DENYLIST := private/denylist.local
PRIVATE := private/contact.private.yaml

.PHONY: build test check private clean

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
	  && $(RUN) python3 scripts/check_denylist.py --public --denylist $(DENYLIST) --private $(PRIVATE) \
	       cv.yaml build/$$v/resolved.json build/$$v/resume.json build/$$v/cv.txt \
	  || exit 1; \
	done
	@echo "check: all variants passed"

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

clean:
	rm -rf build
