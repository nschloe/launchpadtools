VERSION=$(shell python3 -c "import launchpadtools; print(launchpadtools.__version__)")

default:
	@echo "\"make publish\"?"

upload: setup.py
	# Make sure we're on the master branch
	@if [ "$(shell git rev-parse --abbrev-ref HEAD)" != "master" ]; then exit 1; fi
	rm -f dist/*
	python setup.py bdist_wheel --universal
	twine upload dist/*

tag:
	@if [ "$(shell git rev-parse --abbrev-ref HEAD)" != "master" ]; then exit 1; fi
	@echo "Tagging v$(VERSION)..."
	git tag v$(VERSION)
	git push --tags

publish: tag upload

lint:
	black --check setup.py launchpadtools/ test/*.py tools/
	flake8 setup.py launchpadtools/ test/*.py tools/

black:
	black setup.py launchpadtools/ test/*.py tools/*
