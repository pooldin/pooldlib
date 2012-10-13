# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY := clean dev install tests

clean:
	@find . -name "*.py[co]" -exec rm -rf {} \;

install:
	@python setup.py install

dev:
	@python setup.py dev

tests: .FORCE
	@nosetests -v || true

.FORCE:
