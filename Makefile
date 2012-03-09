.PHONY: clean

egg:
	python setup.py bdist_egg

upload:
	python setup.py sdist bdist_egg upload

clean:
	-rm -rf $(BUILDDIR)
	-rm -rf dist
	-rm -rf *.egg-info
	-rm -rf `find . -name *.pyc`