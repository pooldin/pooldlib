# Magical make incantations...
.DEFAULT_GOAL := dev
.PHONY: clean clean-py dev docs docs-clean docs-open install \
	    tests tests-all tests-tag tests-external tests-stripe tests-twilio \
		upload upload-dev upload-nightly upload-release shell ipy bpy

REV=$(shell git rev-parse --short HEAD)
TIMESTAMP=$(shell date +'%s')
RUN=foreman run
MANAGE=$(RUN) python manage.py

shell:
	@$(MANAGE) shell

ipy:
	@$(MANAGE) shell -i

bpy:
	@$(MANAGE) shell -b

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
	@nosetests -vx -a '!external' ${TEST_ARGS} || true

tests-all:
	@nosetests -vx ${TEST_ARGS} || true

tests-external:
	@nosetests -vx -a 'external' ${TEST_ARGS} || true

tests-stripe:
	@nosetests -vx -a 'stripe' ${TEST_ARGS} || true

tests-twilio:
	@nosetests -vx -a 'twilio' ${TEST_ARGS} || true

tests-tag:
	@nosetests -vx -a '${TEST_ARGS}' || true

upload: upload-dev

upload-dev:
	@python setup.py egg_info --tag-build='-dev.$(TIMESTAMP).$(REV)' sdist upload -r pooldin

upload-nightly:
	@python setup.py egg_info --tag-date --tag-build='-dev' sdist upload -r pooldin

upload-release:
	@python setup.py sdist upload -r pooldin
