build: clean LICENSE
	python3 -m pip install setuptools wheel
	python3 setup.py bdist_wheel --universal
	python3 setup.py sdist

clean:
	mkdir -p build dist
	rm -r build dist

publish: build
	python3 -m pip install twine
	python3 -m twine upload -u __token__ -s --sign-with gpg2 dist/*
