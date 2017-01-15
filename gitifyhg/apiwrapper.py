from mercurial.context import memctx, memfilectx
from mercurial.util import version as hg_version
from distutils.version import StrictVersion
from mercurial import extensions

# Conditional imports depending on Mercurial version
if hg_version() >= '4.0.1':
    from mercurial.bookmarks import _readactive
    from mercurial.util import digester
else:
    from mercurial.bookmarks import readcurrent
    from mercurial.util import sha1



# Functions wrapping the Mercurial API. They follow the naming convention of
# hg_[function name]

def hg_readactive(repo):
    if hg_version() >= '4.0.1':
        head = _readactive(repo,repo._bookmarks)
    else:
        head = readcurrent(repo)

def hg_sha1(url):
    if hg_version() >= '4.0.1':
        d = digester(['md5', 'sha1'])
        d.update(url.encode('utf-8'))
        return d['sha1']
    else:
        return sha1(url.encode('utf-8')).hexdigest()

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