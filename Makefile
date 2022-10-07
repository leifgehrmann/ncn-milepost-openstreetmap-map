.PHONY: help
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

install: ## install dependencies
	poetry install

main: main-light main-dark  ## runs the main script which generates the map

main-light: ## runs the main script which generates the light-mode map
	poetry run python main.py --light

main-dark: ## runs the main script which generates the dark-mode map
	poetry run python main.py --dark

lint: ## Checks for linting errors
	poetry run flake8

update-engraver: ## upgrades map-engraver to latest version of master
	poetry remove map-engraver || true
	poetry add git+https://github.com/leifgehrmann/map-engraver.git
	poetry install
