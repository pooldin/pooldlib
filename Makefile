# Magical make incantations...
.PHONY := dev install tests

.DEFAULT_GOAL := dev


SETUP=python setup.py


install:
	@$(SETUP) install

dev:
	@$(SETUP) dev

tests:
	@python test.py
