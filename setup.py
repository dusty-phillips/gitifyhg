from setuptools import setup
setup(
    name="gitifyhg",
    author="Dusty Phillips",
    author_email="dusty@buchuki.com",
    url="https://github.com/buchuki/gitifyhg",
    description="Tools to facilitate using hg git as a git client for hg",
    version="0.2",
    py_modules="gitifyhg",
    install_requires=[
        'path.py',
        'sh',
        'six'
    ],
    entry_points={
        'console_scripts': [
            'gitifyhg = gitifyhg:main',
        ],
    }
)
