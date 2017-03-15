from distutils.core import setup

description = '''Acquieres images of La Palma and stacks them into one image.
Also it can create nightly videos using libav and avconv.
'''

setup(
    name='la_palma_overview',
    version='0.0.3',
    description=description,
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
        'smart_fact_crawler==0.3.0',
        'send2trash',
    ],
    entry_points={'console_scripts': [
        'la_palma_overview = la_palma_overview.__init__:main',
        'la_palma_overview_video = la_palma_overview.la_palma_overview_video:main',
    ]},
    zip_safe=False,
)
