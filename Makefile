.PHONY: clean egg sdist

egg:
	python setup.py bdist_egg

sdist:
	python setup.py sdist

upload: sdist egg
	python setup.py sdist bdist_egg upload

clean:
	-rm -rf $(BUILDDIR)
	-rm -rf dist
	-rm -rf build
	-rm -rf *.egg-info
	-rm -rf `find . -name *.pyc`