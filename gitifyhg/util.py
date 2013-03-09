import os
import sys
import json

from mercurial.node import hex as hghex  # What idiot overroad a builtin?
from mercurial.node import bin as hgbin


DEBUG_GITIFYHG = os.environ.get("DEBUG_GITIFYHG") != None


# hijack stdout to prevent mercurial from inadvertently talking to git.
# interactive=off and ui.pushbuffer() don't seem to work.
class DummyOut(object):
    def write(self, x):
        pass

    def flush(self):
        pass
actual_stdout = sys.stdout
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
            self.marks_version = 2

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

    def upgrade_marks(self, hgrepo):
        if self.marks_version == 1:  # Convert from integer reversions to hgsha1
            log("Upgrading marks-hg from hg sequence number to SHA1", "WARNING")
            self.marks_to_revisions = dict(
                (mark, hghex(hgrepo.changelog.node(int(rev)))) for mark, rev in self.marks_to_revisions.iteritems())
            self.revisions_to_marks = dict(
                (hghex(hgrepo.changelog.node(int(rev))), mark) for rev, mark in self.revisions_to_marks.iteritems())
            self.marks_version = 2
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
