from mercurial.context import memctx, memfilectx
from mercurial.util import version as hg_version
from distutils.version import StrictVersion
from mercurial import extensions

# Conditional imports depending on Mercurial version
if hg_version() >= '3.7': 
    from mercurial.bookmarks import _readactive 
elif hg_version() >= '3.5' and hg_version() < '3.7': 
    from mercurial.bookmarks import readactive
else:
    from mercurial.bookmarks import readcurrent

if hg_version() >= '3.2':
    from mercurial.util import digester 
else:
    from mercurial.util import sha1

if hg_version() >= '3.0':
    from mercurial import exchange
else:
    from mercurial.localrepo import localrepository as exchange
 
# Functions wrapping the Mercurial API. They follow the naming convention of
# hg_[function name]

def hg_pull(repo, peer, heads=None, force=False):
    return exchange.pull(repo, peer, heads=heads, force=force)

def hg_push(repo, peer, force=False, newbranch=None):
    return exchange.push(repo, peer, force=force, newbranch=newbranch)

def hg_readactive(repo):
    if hg_version() >= '3.7': 
        return _readactive(repo,repo._bookmarks) 
    elif hg_version() >= '3.5' and hg_version() < '3.7': 
        return readactive(repo) 
    else: 
        return readcurrent(repo) 

def hg_sha1(url):
    encoded = url.encode('utf-8')

    if hg_version() >= '3.2':
        d = digester(['md5', 'sha1'])
        d.update(encoded)
        return d['sha1']
    else:
        return sha1(encoded).hexdigest()

def hg_memfilectx(repo, path, data, is_link=False, is_exec=False, copied=None):
    if hg_version() >= '3.1':
        return memfilectx(repo, path, data, is_link, is_exec, copied)
    else:
        return memfilectx(path, data, is_link, is_exec, copied)

def hg_strip(repo, processed_nodes):
    class dummyui(object):
        def debug(self, msg):
            pass

    if StrictVersion(hg_version()) >= StrictVersion('2.8'):
        stripext = extensions.load(dummyui(), 'strip', '')
        return stripext.strip(dummyui(), repo, processed_nodes)
    else:
        return repo.mq.strip(repo, processed_nodes)

# Helper Functions to help with changes to the mercurial API

def handle_deleted_file():
    if hg_version() >= '3.2':
        return
    else:
        raise IOError