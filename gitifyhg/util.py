import os
import sys
import json

from mercurial.node import hex as hghex  # What idiot overroad a builtin?
from mercurial.node import bin as hgbin
from mercurial.config import config
from mercurial.scmutil import userrcpath


DEBUG_GITIFYHG = os.environ.get("DEBUG_GITIFYHG") != None


BRANCH = 'branch'
BOOKMARK = 'bookmark'
TAG = 'tag'

actual_stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # Ensure stdout is unbuffered


def deactivate_stdout():
    """Hijack stdout to prevent mercurial from inadvertently talking to git.

    Mere interactive=off and ui.pushbuffer() don't seem to work.
    """
    class DummyOut(object):
        def write(self, x):
            pass

        def flush(self):
            pass
    sys.stdout = DummyOut()


def log(msg, level="DEBUG"):
    '''The git remote operates on stdin and stdout, so all debugging information
    has to go to stderr.'''
    if DEBUG_GITIFYHG or level != "DEBUG":
        sys.stderr.write(u'%s: %r\n' % (level, msg))


def die(msg, *args):
    log(msg, 'ERROR', *args)
    sys.exit(1)


def output(msg=''):
    if isinstance(msg, unicode):
        msg = msg.encode('utf-8')
    log("OUT: %s" % msg)
    print >> actual_stdout, msg


def version():
    """Return version of gitifyhg"""
    try:
        import pkg_resources
        return pkg_resources.get_distribution("gitifyhg").version
    except Exception:
        return "UNKNOWN"


def gittz(tz):
    return '%+03d%02d' % (-tz / 3600, -tz % 3600 / 60)


def gitmode(flags):
    if 'l' in flags:
        return '120000'
    elif 'x' in flags:
        return '100755'
    else:
        return '100644'


def hgmode(mode):
    modes = {'100755': 'x', '120000': 'l'}
    return modes.get(mode, '')


def hg_to_git_spaces(name):
    '''Spaces are allowed in mercurial, but not in git. We convert them to
    the unlikely string ___'''
    return name.replace(' ', '___')


def git_to_hg_spaces(name):
    '''But when we push back to mercurial, we need to convert it the other way.'''
    return name.replace('___', ' ')


def branch_tip(repo, branch):
    '''HG has a lovely branch_tip method, but it requires mercurial 2.4
    This function provides backwards compatibility. If we ever get to
    drop older versions, we can drop this function.'''
    if hasattr(repo, 'branchtip'):
        return repo.branchtip(branch)
    else:
        return repo.branchtags()[branch]


def branch_head(hgremote, branch):
    try:
        heads = hgremote.branches[branch]
    except KeyError:
        return

    if len(heads) > 1:
        log("Branch '%s' has more than one head, consider merging" % (
            branch), "WARNING")
        tip = branch_tip(hgremote.repo, branch)
    else:
        tip = heads[0]

    return hgremote.repo[tip]


def ref_to_name_reftype(ref):
    '''Converts a git ref into a name (e.g., the name of that branch, tag, etc.)
    and its hg type (one of BRANCH, BOOKMARK, or TAG).'''
    if ref == 'refs/heads/master':
        return ('default', BRANCH)
    elif ref.startswith('refs/heads/branches/'):
        return (ref[len('refs/heads/branches/'):], BRANCH)
    elif ref.startswith('refs/heads/'):
        return (ref[len('refs/heads/'):], BOOKMARK)
    elif ref.startswith('refs/tags/'):
        return (ref[len('refs/tags/'):], TAG)
    else:
        assert False, "unexpected ref: %s" % ref


def name_reftype_to_ref(name, reftype):
    '''Converts a name and type (e.g., '1.0' and 'tags') into a git ref.'''
    if reftype == BRANCH:
        if name == 'default':
            return 'refs/heads/master'
        else:
            return 'refs/heads/branches/%s' % name
    elif reftype == BOOKMARK:
        return 'refs/heads/%s' % name
    elif reftype == TAG:
        return 'refs/tags/%s' % name
    assert False, "unknown reftype: %s" % reftype


def user_config():
    """Read the Mercurial user configuration

    This is typically ~/.hgrc on POSIX.  This is returned
    as a Mercurial.config.config object.
    """
    hgrc = config()
    for cfg in userrcpath():
        if not os.path.exists(cfg):
            log("NOT reading missing cfg: " + cfg)
            continue
        log("Reading config: " + cfg)
        hgrc.read(cfg)
    return hgrc


def relative_path(path):
    """Ensure path is relative"""
    return os.path.relpath(path, '/') if os.path.isabs(path) else path


class HGMarks(object):
    '''Maps integer marks to specific string mercurial revision identifiers.
    Identifiers are passed as binary nodes and converted to/from hex strings
    before and after storage.'''

    def __init__(self, storage_path):
        ''':param storage_path: The file that marks are stored in between calls.
        Marks are stored in json format.'''
        self.storage_path = storage_path
        self.load()

    def load(self):
        '''Load the marks from the storage file'''
        if self.storage_path.exists():
            with self.storage_path.open() as file:
                loaded = json.load(file)

            self.tips = loaded['tips']
            self.revisions_to_marks = loaded['revisions_to_marks']
            self.last_mark = loaded['last-mark']
            self.marks_to_revisions = dict([(int(v), k) for k, v in
                    self.revisions_to_marks.iteritems()])
            self.notes_mark = loaded.get('notes-mark', None)
            self.marks_version = loaded.get('marks-version', 1)
        else:
            self.tips = {}
            self.revisions_to_marks = {}
            self.marks_to_revisions = {}
            self.last_mark = 0
            self.notes_mark = None
            self.marks_version = 3

    def store(self):
        '''Save marks to the storage file.'''
        with self.storage_path.open('w') as file:
            json.dump({
                'tips': self.tips,
                'revisions_to_marks': self.revisions_to_marks,
                'last-mark': self.last_mark,
                'notes-mark': self.notes_mark,
                'marks-version': self.marks_version},
            file)

    def upgrade_marks(self, hgremote):
        if self.marks_version == 1:  # Convert from integer reversions to hgsha1
            log("Upgrading marks-hg from hg sequence number to SHA1", "WARNING")
            self.marks_to_revisions = dict(
                (mark, hghex(hgremote.repo.changelog.node(int(rev)))) for mark, rev in self.marks_to_revisions.iteritems())
            self.revisions_to_marks = dict(
                (hghex(hgremote.repo.changelog.node(int(rev))), mark) for rev, mark in self.revisions_to_marks.iteritems())
            self.marks_version = 2
            log("Upgrade complete", "WARNING")
        if self.marks_version == 2:  # Convert tips to use gitify refs as keys
            log("Upgrading marks-hg tips", "WARNING")
            self.tips = dict(
                ("%s/%s" % (hgremote.prefix, reftype_and_name), tip) for reftype_and_name, tip in self.tips.iteritems())
            self.marks_version = 3
            log("Upgrade complete", "WARNING")

    def mark_to_revision(self, mark):
        return hgbin(self.marks_to_revisions[mark])

    def revision_to_mark(self, revision):
        return self.revisions_to_marks[hghex(revision)]

    def get_mark(self, revision):
        self.last_mark += 1
        self.revisions_to_marks[hghex(revision)] = self.last_mark
        return self.last_mark

    def new_mark(self, revision, mark):
        self.revisions_to_marks[hghex(revision)] = mark
        self.marks_to_revisions[mark] = hghex(revision)
        self.last_mark = mark

    def is_marked(self, revision):
        return hghex(revision) in self.revisions_to_marks

    def new_notes_mark(self):
        self.last_mark += 1
        self.notes_mark = self.last_mark
        return self.notes_mark


class GitMarks(object):
    '''Maps integer marks to git commit hashes.'''

    def __init__(self, storage_path):
        ''':param storage_path: The file that marks are stored in between calls.'''
        self.storage_path = storage_path
        self.load()

    def load(self):
        '''Load the marks from the storage file.'''
        # TODO: Combine remove_processed_git_marks with this, perhaps by using
        # an OrderedDict to write entires back out in the order they came in.
        self.marks_to_hashes = {}
        if self.storage_path.exists():
            with self.storage_path.open() as file:
                for line in file:
                    if not line.startswith(':'):
                        die("invalid line in marks-git: " + line)
                    mark, sha1 = line[1:].split()
                    self.marks_to_hashes[mark] = sha1

    def has_mark(self, mark):
        return str(mark) in self.marks_to_hashes

    def mark_to_hash(self, mark):
        return self.marks_to_hashes[str(mark)]

