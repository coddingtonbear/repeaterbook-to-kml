import os
from setuptools import setup, find_packages
import sys
import uuid


requirements_path = os.path.join(
    os.path.dirname(__file__),
    'requirements.txt',
)
try:
    from pip.req import parse_requirements
    requirements = [
        str(req.req) for req in parse_requirements(
            requirements_path,
            session=uuid.uuid1()
        )
    ]
except ImportError:
    requirements = []
    with open(requirements_path, 'r') as in_:
        requirements = [
            req for req in in_.readlines()
            if not req.startswith('-')
            and not req.startswith('#')
        ]


setup(
    name='repeaterbook-to-kml',
    version='0.1',
    url='https://github.com/coddingtonbear/repeaterbook-to-kml',
    description=(
        'Convert CHIRP-Format CSV files exported from Repeaterbook into KML'
        ' files'
    ),
    author='Adam Coddington',
    author_email='me@adamcoddington.net',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'repeaterbook-to-kml = repeaterbook_to_kml:cmdline'
        ]
    },
    include_package_data = True,
    install_requires=requirements,
    packages=find_packages(),
)
