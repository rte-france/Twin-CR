PLAYBOOK = site.yml
ENV ?= dev
TARGET ?= deb
TAGS ?=
EXTRA ?=

TAG_OPT = $(if $(TAGS),--tags "$(TAGS)",)

VENV = .venv
PYTHON = $(VENV)/bin/python
ANSIBLE = $(VENV)/bin/ansible-playbook

.PHONY: help venv deploy dev dev-mac opf vault-edit vault-create

help:
	@echo "Twin-CR Infrastructure Automation (DevSecOps)"
	@echo "  make deploy [ENV=dev|opf] [INVENTORY=path]   - Deploy infrastructure"
	@echo "  make dev                                     - Shortcut for dev"

$(ANSIBLE):
	@python3 -m venv $(VENV)
	@$(VENV)/bin/pip install --quiet --upgrade pip ansible

$(VENV): $(ANSIBLE)

venv: $(ANSIBLE)

# Resolve inventory dynamically based on ENV
INVENTORY ?= inventories/$(ENV).ini

deploy: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

dev: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

dev-mac: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

opf: $(VENV)
	@$(ANSIBLE) -i inventories/opf.ini $(PLAYBOOK) $(TAG_OPT) $(EXTRA)
