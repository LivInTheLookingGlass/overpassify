import os.path

try:
    import setuptools
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


classifiers = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
    'Operating System :: OS Independent',
    'Topic :: Internet',
    'Topic :: Scientific/Engineering :: GIS',
    'Topic :: Software Development :: Compilers',
    'Programming Language :: Other',
    'Programming Language :: Python'
]


classifiers.extend((('Programming Language :: Python :: %s' % x)
                    for x in '2 3 2.7 3.3 3.4 3.5 3.6'.split()))


def main():
    setup(
        name = 'overpassify',
        version = '1.0.0',
        author = 'Olivia Appleton',
        author_email = 'olivia.kay.appleton@gmail.com',
        description = 'A tool to more easily develop queries of OpenStreetMap',
        license = 'LGPLv3',
        keywords = 'OSM OpenStreetMap Overpass OverpassQL Transpiler Compiler Query',
        packages=['overpassify'],
        long_description=read('README.rst'),
        url='https://github.com/LivInTheLookingGlass/overpassify',
        install_require=('dill',),
        classifiers=classifiers
    )


if __name__ == '__main__':
    main()
