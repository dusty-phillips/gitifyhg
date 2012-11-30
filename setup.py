from setuptools import setup, find_packages
setup(
    name="gitifyhg",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'path.py',
        'sh'
    ],
    entry_points={
        'console_scripts': [
            'gitifyhg = gitifyhg:gitify',
        ],
    }
)
