build: clean LICENSE
	python3 setup.py bdist_wheel --universal
	python3 setup.py sdist

clean:
	mkdir -p build dist
	rm -r build dist

publish: build
	twine upload -u LivInTheLookingGlass -s --sign-with gpg2 dist/*
