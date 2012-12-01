from setuptools import setup, find_packages
setup(
    name="gitifyhg",
    author="Dusty Phillips",
    author_email="dusty@buchuki.com",
    url="https://github.com/buchuki/gitifyhg",
    version="0.2",
    py_modules="gitifyhg",
    install_requires=[
        'path.py',
        'sh'
    ],
    entry_points={
        'console_scripts': [
            'gitifyhg = gitifyhg:main',
        ],
    }
)
