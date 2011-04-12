from setuptools import setup

setup(
    name='infra',
    version='0.1',
    packages=['infra'],
    entry_points={
        'console_scripts': [
            'infra = infra:main',
        ],
    },
    install_requires=[
        'eventlet',
    ]
)
