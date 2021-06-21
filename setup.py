from distutils.core import setup

description = '''Acquires images of La Palma and stacks them into one image.
It can also create nightly videos using ffmpeg.
'''

setup(
    name='la_palma_overview',
    version='0.2.0',
    description=description,
    url='https://github.com/fact-project/la_palma_overview.git',
    author='Sebastian Mueller,Maximilian Noethe',
    author_email='sebmuell@phys.ethz.ch',
    license='MIT',
    packages=[
        'la_palma_overview',
    ],
    install_requires=[
        'docopt',
        'scikit-image',
        'requests',
        'smart_fact_crawler @ https://github.com/fact-project/smart_fact_crawler/archive/v0.7.0.tar.gz',
        'send2trash',
        'pillow>=8',
    ],
    entry_points={'console_scripts': [
        'la_palma_overview = la_palma_overview.__init__:main',
        'la_palma_overview_video = la_palma_overview.la_palma_overview_video:main',
    ]},
    zip_safe=False,
)
