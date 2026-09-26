.PHONY: validate test bundle

PYTHON ?= python3

validate:
	$(PYTHON) scripts/artifactctl.py validate
	$(PYTHON) scripts/artifactctl.py notices --output THIRD_PARTY_NOTICES.md
	git diff --exit-code -- THIRD_PARTY_NOTICES.md
	$(PYTHON) -m unittest discover -s tests -v

bundle:
	mkdir -p .out
	$(PYTHON) scripts/artifactctl.py build-bundle --output .out/bootstrap-bundle.tgz

test: validate
