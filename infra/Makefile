PLAYBOOK = site.yml
# Applications, deployed once their images are pushed to the registry of the cluster (deployed by PLAYBOOK)
APPS_PLAYBOOK = apps.yml
ENV ?= dev
TARGET ?= deb
TAGS ?=
EXTRA ?=

TAG_OPT = $(if $(TAGS),--tags "$(TAGS)",)

VENV = .venv
PYTHON = $(VENV)/bin/python
ANSIBLE = $(VENV)/bin/ansible-playbook

.PHONY: help venv deploy dev dev-mac opf apps vault-edit vault-create

help:
	@echo "Twin-CR Infrastructure Automation (DevSecOps)"
	@echo "  make deploy [ENV=dev|opf] [INVENTORY=path]   - Deploy infrastructure"
	@echo "  make dev                                     - Shortcut for dev"
	@echo "  make apps [ENV=dev|opf] [INVENTORY=path]     - Deploy the applications (images pushed first)"

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

apps: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(APPS_PLAYBOOK) $(TAG_OPT) $(EXTRA)
