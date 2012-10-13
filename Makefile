# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY: clean clean-py dev docs docs-clean docs-open install tests


clean:
	@$(MAKE) docs-clean clean-py

clean-py:
	find . -name "*.py[co]" -exec rm -rf {} \;

dev:
	@python setup.py dev
	@$(MAKE) docs

docs:
	@git submodule update
	@$(MAKE) -C docs html

docs-clean:
	@$(MAKE) -C docs clean

docs-open:
	@open docs/_build/html/index.html

install:
	@python setup.py install

tests:
	@nosetests -v || true
