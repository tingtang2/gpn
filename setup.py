from setuptools import setup


install_requires = [
    "transformers[torch]",
    "datasets",
    "pyarrow",
    "pandas",
    "numpy",
    "torchinfo",
    "biopython",
    "wandb",
]


setup(
    name='plantbert',
    version='0.1',
    description='plantbert',
    url='http://github.com/gonzalobenegas/plantbert',
    author='Gonzalo Benegas',
    author_email='gbenegas@berkeley.edu',
    license='MIT',
    packages=['plantbert'],
    zip_safe=False,
    install_requires=install_requires
)
