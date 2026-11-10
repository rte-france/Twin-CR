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
	@echo "TwinEU Infrastructure Automation (DevSecOps)"
	@echo "  make deploy [ENV=dev|opf] [TARGET=deb|orb]  - Deploy infrastructure"
	@echo "  make dev                                     - Shortcut for dev (Debian/Docker)"
	@echo "  make dev-mac                                 - Shortcut for dev (Mac/OrbStack)"
	@echo "  make opf                                     - Shortcut for OPF production"
	@echo "  make vault-edit [ENV=dev|opf]                - Edit encrypted secrets"
	@echo "  make vault-create [ENV=dev|opf]              - Create encrypted secrets"

$(VENV):
	@python3 -m venv $(VENV)
	@$(VENV)/bin/pip install --quiet --upgrade pip ansible

venv: $(VENV)

# Resolve inventory dynamically based on ENV and TARGET
ifeq ($(ENV),dev)
  ifeq ($(TARGET),orb)
    INVENTORY = environments/dev/inventory_orb.ini
  else
    INVENTORY = environments/dev/inventory_deb.ini
  endif
else
  INVENTORY = environments/$(ENV)/inventory.ini
endif

deploy: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

dev: $(VENV)
	@$(ANSIBLE) -i $(INVENTORY) $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

dev-mac: $(VENV)
	@$(ANSIBLE) -i environments/dev/inventory_orb.ini $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

opf: $(VENV)
	@$(ANSIBLE) -i environments/opf/inventory.ini $(PLAYBOOK) $(TAG_OPT) $(EXTRA)

vault-edit: $(VENV)
	@$(VENV)/bin/ansible-vault edit environments/$(ENV)/group_vars/all/secrets.yml

vault-create: $(VENV)
	@mkdir -p environments/$(ENV)/group_vars/all
	@$(VENV)/bin/ansible-vault create environments/$(ENV)/group_vars/all/secrets.yml
