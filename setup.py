from setuptools import setup, find_packages
import sys
import os

py = sys.version_info[:2]

if py > (2, 7) or py < (2, 7):
    raise RuntimeError('Python 2.7 is required')

root = os.path.abspath(os.path.dirname(__file__))

README = os.path.join(root, 'README.md')
if os.path.isfile(README):
    README = open(README).read()
else:
    README = None

version = '0.1'

# Specify non-pypi dependency links (i.e. locate poold.in and github packages)
stripe = 'https://code.stripe.com'

links = [
    stripe,
]

install_requires = [
    'pytz==2012d',
    'psycopg2==2.4.5',
    'cdecimal==2.3',
    'cement==2.0.2',
    'Werkzeug>=0.7',
    'SQLAlchemy',
    'stripe',
    'twilio',
]

tests_require = [
    'nose==1.2.1',
    'mock==1.0.0',
    'coverage==3.5.2',
]

docs_require = [
    'Sphinx==1.1.3',
]

entry_points = dict()

setup(name='pooldlib',
      version=version,
      description='The foundational library which defines Poold.in and is '
                  'used by pooldwww and pooldREST.',
      long_description=README,
      keywords='library',
      author='Brian Oldfield',
      author_email='brian@poold.in',
      url='http://poold.in',
      license='PRIVATE',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      extras_require=dict(tests=tests_require, docs=docs_require),
      install_requires=install_requires,
      entry_points=entry_points,
      scripts=[],
      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Poold.in'])
