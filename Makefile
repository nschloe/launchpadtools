
default:
	@echo "\"make release\"?"

README.rst: README.md
	pandoc README.md -o README.rst
	python setup.py check -r -s || exit 1

upload: setup.py README.rst
	python setup.py sdist upload --sign

V=`python -c "import launchpadtools; print(launchpadtools.__version__)"`
tag:
	git tag -a `@echo -n v$V` -m "tagging v$V" && git push --tags

release: upload tag

clean:
	rm -rf \
	 README.rst \
	 launchpadtools.egg-info/ \
	 dist
