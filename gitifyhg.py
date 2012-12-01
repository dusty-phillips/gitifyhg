import sh
from path import path as p
import sys
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser


def gitifyhg():
    '''Call this function to initialize a git checkout in an existing local hg
    repository.'''

    if not p('.hg').isdir():
        sys.exit('There is no .hg directory. Are you at the top'
            ' of the repository?')

    hgconfig = ConfigParser()
    hgconfig.read('.hg/hgrc')
    for section in ('git', 'extensions'):
        if not hgconfig.has_section(section):
            hgconfig.add_section(section)
    hgconfig.set('git', 'intree', '1')
    hgconfig.set('extensions', 'bookmarks', '')
    hgconfig.set('extensions', 'hggit', '')
    with open('.hg/hgrc', 'w') as file:
        hgconfig.write(file)

    sh.git.init()
    sh.hg.bookmark('master', '-r', 'default')
    sh.hg.gexport()
    sh.git.reset('--hard')
    sh.git.config('core.excludesfile', p('.hgignore'))
    sh.git.config('alias.hgpull', '!gitifyhg hgpull')
    sh.git.config('alias.hgpush', '!gitifyhg hgpush')
    with p('.git/info/exclude').open('a') as f:
        f.write('.hg*\n')


def hgpull():
    '''Attempts to sync up git's master with upstream's default. This works
    kinda like git-svn, we aren't trying to merge multiple branches and stuff,
    yet, just trying to make those two branches coincide.

    This is tricky because they are operating on the same working directory,
    so we end up doing a series of updates and resets to get everything lined
    up. Thus it can be potentially destructive.'''
    sh.hg.pull()
    sh.hg.bookmark('-f', '-r', 'default', 'master')
    sh.hg.gexport()
    sh.hg.update()
    sh.git.checkout('master')
    sh.git.reset('--hard', 'master')


def hgpush():
    '''Attempts to sync up upstreams default with git's master. This is less
    tricky if you recently did an hgpull and everything is satisfactory.

    One thing to watch out here is gimport imports all git branches as
    bookmarks. Therefor, you should not have any working branches on git that
    have commits not on master, or they will create new heads in the mercurial
    repo. I have some ideas to use hg strip to allow branches to stay local
    in git, but nothing is implemented yet.'''

    sh.git.checkout('master')
    sh.hg.gimport()
    sh.hg.update()
    sh.hg.push()


def main():
    if len(sys.argv) == 1:
        gitifyhg()
    elif sys.argv[1] in ('hgpush', 'hgpull'):
        globals()[sys.argv[1]]()
