# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY := dev install tests


install:
	@python setup.py install

dev:
	@python setup.py dev

tests: .FORCE
	@nosetests || true

.FORCE:
