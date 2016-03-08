from distutils.core import setup

setup(
    name='la_palma_overview',
    version='0.0.1',
    description='acquieres images of La Palma and stacks them into one',
    url='https://github.com/fact-project/la_palma_overview.git',
    author='Sebastian Mueller',
    author_email='sebmuell@phys.ethz.ch',
    license='MIT',
    packages=[
        'la_palma_overview',
    ],
    install_requires=[
        'docopt',
        'scikit-image',
        'requests',
        'smart_fact_crawler',
    ],
    entry_points={'console_scripts': [
        'la_palma_overview = la_palma_overview.__init__:main',
    ]},
    zip_safe=False,
)
