# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY := dev install tests


SETUP=python setup.py
SETUP=nosetests


install:
	@$(SETUP) install

dev:
	@$(SETUP) dev

tests: .FORCE
	@nosetests || true

.FORCE:
