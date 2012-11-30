import sh
from path import path as p
import sys
from configparser import ConfigParser


def gitify():
    '''Call this function (probably as an entry point) to initialize a git
    checkout in an existing local hg repository.'''

    if not p('.hg').isdir():
        sys.exit('There is no .hg directory. Are you at the top'
            ' of the repository?')

    hgconfig = ConfigParser()
    hgconfig.read('.hg/hgrc')
    for section in ('git', 'extensions'):
        if not hgconfig.has_section(section):
            hgconfig.add_section(section)
    hgconfig['git']['intree'] = '1'
    hgconfig['extensions']['bookmarks'] = ''
    hgconfig['extensions']['hggit'] = ''
    with open('.hg/hgrc', 'w') as file:
        hgconfig.write(file)

    sh.git.init()
    sh.hg.bookmark('hg/default', '-r', 'default')
    sh.hg.gexport()
    sh.git.branch('--track', 'master', 'hg/default')
    sh.git.reset('--hard')
    sh.git.config('core.excludesfile', p('.hgignore'))
    with p('.git/info/exclude').open('a') as f:
        f.write('.hg*\n')

    gitconfig = ConfigParser()
    gitconfig.read('.git/config')
    if not gitconfig.has_section('alias'):
        gitconfig.add_section('alias')
    gitconfig['alias']['hgpull'] = '!"hg pull ; hg gexport"'
    gitconfig['alias']['hgpush'] = '!"hg gimport ; hg update ; hg push"'
    with open('.git/config', 'w') as file:
        gitconfig.write(file)

