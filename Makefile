# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY: clean clean-docs clean-py dev docs install tests

clean:
	@$(MAKE) clean-docs clean-py

clean-docs:
	@$(MAKE) -C docs clean

clean-py:
	find . -name "*.py[co]" -exec rm -rf {} \;

dev:
	@git submodule update
	@python setup.py dev
	@$(MAKE) docs

docs:
	@$(MAKE) -C docs html

install:
	@python setup.py install

tests:
	@nosetests -v || true
