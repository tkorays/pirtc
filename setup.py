from setuptools import setup, find_packages
version = '0.1.0'

setup(
    name='pirtc',
    version=version,
    description='Algorithm tools for WebRTC written with python',
    author='tkorays',
    author_email='tkorays@hotmail.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    scripts=[],
    data_files=[],
    entry_points={},
    install_requires=[
        'numpy',
        'pandas',
    ],
    dependency_links=[],
    long_description='''
    Algorithm tools for WebRTC written with python
    '''
)
