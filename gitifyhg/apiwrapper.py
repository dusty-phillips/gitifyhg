from mercurial.context import memctx, memfilectx
from mercurial.util import version as hg_version
from distutils.version import StrictVersion

def hg_memfilectx(repo, path, data, is_link=False, is_exec=False, copied=None):
    if hg_version() >= '3.1':
        return memfilectx(repo, path, data, is_link, is_exec, copied)
    else:
        return memfilectx(path, data, is_link, is_exec, copied)

def strip_revs(repo, processed_nodes):
    class dummyui(object):
        def debug(self, msg):
            pass

    if StrictVersion(hg_version()) >= StrictVersion('2.8'):
        stripext = extensions.load(dummyui(), 'strip', '')
        return stripext.strip(dummyui(), repo, processed_nodes)
    else:
        return repo.mq.strip(repo, processed_nodes)