.PHONY: help validate skills clean

SKILL_NAME := workflow-gtm-agent
SKILL_DIR := skills/$(SKILL_NAME)
SKILL_FILE := $(SKILL_DIR)/SKILL.md
PYTHON ?= python3
VALIDATE_VENV ?= .venv-validate
VALIDATE_STAMP := $(VALIDATE_VENV)/.pyyaml-installed
ifeq ($(OS),Windows_NT)
VALIDATE_PYTHON := $(VALIDATE_VENV)/Scripts/python.exe
else
VALIDATE_PYTHON := $(VALIDATE_VENV)/bin/python
endif

help:
	@echo "Targets:"
	@echo "  make validate  Validate SKILL.md"
	@echo "  make skills    Build skill package into ./$(SKILL_DIR)/"
	@echo "  make clean     Remove local cache artifacts"

$(VALIDATE_STAMP):
	$(PYTHON) -m venv "$(VALIDATE_VENV)"
	"$(VALIDATE_PYTHON)" -m pip install --quiet --disable-pip-version-check --no-cache-dir --upgrade pip pyyaml
	@touch "$(VALIDATE_STAMP)"

validate: $(VALIDATE_STAMP)
	@"$(VALIDATE_PYTHON)" scripts/validate_skill.py "$(SKILL_FILE)" --name "$(SKILL_NAME)"

clean:
	@rm -rf "$(VALIDATE_VENV)"
	@find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete

skills: validate
	@mkdir -p "$(SKILL_DIR)"
	@echo "Built skill in $(SKILL_DIR)/"
