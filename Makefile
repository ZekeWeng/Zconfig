# zconfig — entrypoint. Run `make` for the menu.
.DEFAULT_GOAL := help

SHELLS := install.sh $(shell find lib bootstrap tools platform scripts -name '*.sh' 2>/dev/null)

.PHONY: help install install-corp update backup check lint all

help:        ## Show this menu
	@awk 'BEGIN{FS=":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-10s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)

install:     ## Run the installer (symlinks, per-tool installs)
	@./install.sh

install-corp: ## Like install but skips downloads (configs + identity only)
	@ZCONFIG_PROFILE=corp ./install.sh

update:      ## Pull repo, upgrade brew, sync nvim plugins
	@./scripts/update.sh

backup:      ## Snapshot ~/ dotfiles to ~/.zconfig_backup
	@./scripts/backup.sh

check:       ## Bash syntax check every shell script
	@for f in $(SHELLS); do bash -n "$$f" || exit 1; done
	@echo "syntax ok ($(words $(SHELLS)) files)"

lint:        ## Shellcheck every shell script (severity: warning)
	@command -v shellcheck >/dev/null || { echo "install shellcheck: brew install shellcheck"; exit 1; }
	@shellcheck -S warning $(SHELLS)

all: check lint  ## Run check + lint
