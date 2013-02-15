# Copyright 2012-2013 Dusty Phillips

# This file is part of gitifyhg.

# gitifyhg is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gitifyhg is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.

# Some of this code comes from https://github.com/felipec/git/tree/fc/remote/hg
# but much of it has been rewritten.


import sys
import os
import json
import re
import subprocess
from path import path as p
from time import strftime


# Enable "plain" mode to make us resilient against changes to the locale, as we
# rely on parsing certain messages produced by Mercurial. See issue #26.
os.environ['HGPLAIN'] = '1'
# Disable loading of the user's $HOME/.hgrc as extensions can cause weird
# interactions and it's better to run in a known state.
os.environ['HGRCPATH'] = ''


from mercurial.ui import ui
from mercurial.context import memctx, memfilectx
from mercurial.error import Abort
from mercurial import encoding
from mercurial.bookmarks import listbookmarks, readcurrent, pushbookmark
from mercurial.util import sha1
from mercurial import hg
from mercurial.node import hex as hghex  # What idiot overroad a builtin?
from mercurial.node import short as hgshort
from mercurial.scmutil import revsingle


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


AUTHOR = re.compile(r'^([^<>]+)?(<(?:[^<>]*)>| [^ ]*@.*|[<>].*)$')


def sanitize_author(author):
    '''Mercurial allows a more freeform user string than git, so we have to
    massage it to be compatible. Git expects "name <email>".'''
    name = ''
    email = 'unknown'
    author = author.replace('"', '')
    match = AUTHOR.match(author)
    if match:
        if match.group(1):  # handle 'None', e.g for input "<only@email>"
            name = match.group(1).strip()
        email = match.group(2).translate(None, "<>").strip()
    else:
        author = author.translate(None, "<>").strip()
        if "@" in author:
            email = author
        else:
            name = author

    if name:
        return "%s <%s>" % (name, email)
    else:
        return "<%s>" % (email)


def branch_tip(repo, branch):
    '''HG has a lovely branch_tip method, but it requires mercurial 2.4
    This function provides backwards compatibility. If we ever get to
    drop older versions, we can drop this function.'''
    if hasattr(repo, 'branchtip'):
        return repo.branchtip(branch)
    else:
        return repo.branchtags()[branch]


class HGMarks(object):
    '''Maps integer marks to specific string mercurial revision identifiers.'''

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
        else:
            self.tips = {}
            self.revisions_to_marks = {}
            self.marks_to_revisions = {}
            self.last_mark = 0
            self.notes_mark = None

    def store(self):
        '''Save marks to the storage file.'''
        with self.storage_path.open('w') as file:
            json.dump({
                'tips': self.tips,
                'revisions_to_marks': self.revisions_to_marks,
                'last-mark': self.last_mark,
                'notes-mark': self.notes_mark},
            file)

    def mark_to_revision(self, mark):
        # not sure making this an int is a good thing...
        return int(self.marks_to_revisions[mark])

    def revision_to_mark(self, revision):
        return self.revisions_to_marks[str(revision)]

    def get_mark(self, revision):
        self. last_mark += 1
        self.revisions_to_marks[str(revision)] = self.last_mark
        return self.last_mark

    def new_mark(self, revision, mark):
        self.revisions_to_marks[str(revision)] = mark
        self.marks_to_revisions[mark] = int(revision)
        self.last_mark = mark

    def is_marked(self, revision):
        return str(revision) in self.revisions_to_marks

    def new_notes_mark(self):
        self.last_mark += 1
        self.notes_mark = self.last_mark
        return self.notes_mark


class GitRemoteParser(object):
    '''Parser for stdin that processes the git-remote protocol.'''

    def __init__(self):
        self.peek_stack = []
        self.read_line()

    def read_line(self):
        '''Read a line from the standard input.'''
        if self.peek_stack:
            self.line = self.peek_stack.pop(0)
        else:
            self.line = sys.stdin.readline().strip()
        log("INPUT: %s" % self.line)
        return self.line

    def peek(self):
        '''Look at the next line and store it so that it can still be returned
        by read_line.'''
        line = sys.stdin.readline().strip()
        self.peek_stack.append(line)
        return line

    def read_mark(self):
        '''The remote protocol contains lines of the format mark: number.
        Return the mark.'''
        return int(self.read_line().partition(':')[-1])

    def read_data(self):
        '''Read all data following a data line for the given number of bytes'''
        self.read_line()
        if not self.line.startswith('data'):
            return None
        size = int(self.line.partition(' ')[-1])
        return sys.stdin.read(size)

    def read_author(self):
        '''Read and parse an author string. Return a tuple of
        (user string, date, git_tz).'''
        self.read_line()
        AUTHOR_RE = re.compile(r'^(?:author|committer|tagger)(?: ([^<>]+)?)? <([^<>]*)> (\d+) ([+-]\d+)')
        match = AUTHOR_RE.match(self.line)
        if not match:
            return None

        user, email, date, tz = match.groups()
        if user is None:
            user = ''
        user += ' <' + email + '>'

        date = int(date)
        tz = -((int(tz) / 100) * 3600) + ((int(tz) % 100) * 60)
        return (user, date, tz)

    def read_block(self, sentinel):
        '''Yield a block of lines one by one until the sentinel value
        is returned. Sentinel may be an empty string, 'done', or other values
        depending on what block is being read.'''
        while self.line != sentinel:
            yield self.line
            self.line = self.read_line()


class HGRemote(object):
    def __init__(self, alias, url):
        if hg.islocal(url.encode('utf-8')):
            url = p(url).abspath()
            # Force git to use an absolute path in the future
            cmd = ['git', 'config', 'remote.%s.url' % alias, "gitifyhg::%s" % url]
            subprocess.call(cmd)

        # use hash of URL as unique identifier in various places.
        # this has the advantage over 'alias' that it stays constant
        # when the user does a "git remote rename old new".
        self.uuid = sha1(url.encode('utf-8')).hexdigest()

        gitdir = p(os.environ['GIT_DIR'].decode('utf-8'))
        self.remotedir = gitdir.joinpath('hg', self.uuid)
        self.marks_git_path = self.remotedir.joinpath('marks-git')
        self.marks = HGMarks(self.remotedir.joinpath('marks-hg'))
        self.parsed_refs = {}
        self.blob_marks = {}
        self.branches = {}
        self.bookmarks = {}

        self.prefix = 'refs/hg/%s' % alias
        self.alias = alias
        self.url = url
        self.build_repo(url)

    def build_repo(self, url):
        '''Make the Mercurial repo object self.repo available. If the local
        clone does not exist, clone it, otherwise, ensure it is fetched.'''
        myui = ui()
        myui.setconfig('ui', 'interactive', 'off')
        myui.setconfig('extensions', 'mq', '')

        local_path = self.remotedir.joinpath('clone')
        if not local_path.exists():
            self.peer, dstpeer = hg.clone(myui, {}, url.encode('utf-8'),
                local_path.encode('utf-8'), update=False, pull=True)
            self.repo = dstpeer.local()
        else:
            self.repo = hg.repository(myui, local_path.encode('utf-8'))
            self.peer = hg.peer(myui, {}, url.encode('utf-8'))
            self.repo.pull(self.peer, heads=None, force=True)

    def process(self):
        '''Process the messages coming in on stdin using the git-remote
        protocol and respond appropriately'''
        parser = GitRemoteParser()

        for line in parser.read_block(''):
            command = line.split()[0]
            if command not in ('capabilities', 'list', 'import', 'export'):
                die('unhandled command: %s' % line)
            getattr(self, 'do_%s' % command)(parser)
            actual_stdout.flush()

        self.marks.store()

    def do_capabilities(self, parser):
        '''Process the capabilities request when incoming from git-remote.
        '''
        output(u"import")
        output(u"export")
        output(u"refspec refs/heads/branches/*:%s/branches/*" % self.prefix)
        output(u"refspec refs/heads/*:%s/bookmarks/*" % self.prefix)
        output(u"refspec refs/tags/*:%s/tags/*" % self.prefix)

        if self.marks_git_path.exists():
            output(u"*import-marks %s" % self.marks_git_path)
        output(u"*export-marks %s" % self.marks_git_path)

        output()

    def do_list(self, parser):
        '''List all references in the mercurial repository. This includes
        the current head, all branches, tags, and bookmarks.'''

        current_branch = self.repo.dirstate.branch()

        # Update the head reference
        head = readcurrent(self.repo)
        if head:
            node = self.repo[head]
        else:
            # If there is no bookmark for head, mock one
            head = current_branch
            node = self.repo['.']
            # I think this means an initial clone occured and we haven't
            # hg updated yet in the local clone
            if not node:
                if 'default' in self.repo:
                    node = self.repo['default']
                else:  # empty repository or head is at 0 commit
                    output()
                    return
            head = head if head != 'default' else 'master'
            #self.bookmarks[head] = node

        self.headnode = (head, node)

        # Update the bookmark references
        for bookmark, node in listbookmarks(self.repo).iteritems():
            self.bookmarks[bookmark] = self.repo[node]

        # update the named branch references
        for branch in self.repo.branchmap():
            heads = self.repo.branchheads(branch, closed=True)
            if heads:
                self.branches[branch] = heads

        # list the head reference
        output("@refs/heads/%s HEAD" % self.headnode[0])

        # list the named branch references
        for branch in self.branches:
            if branch != "default":
                output("? refs/heads/branches/%s" % hg_to_git_spaces(branch))
            else:
                output("? refs/heads/master")

        # list the bookmark references
        for bookmark in self.bookmarks:
            if bookmark != "master":
                output("? refs/heads/%s" % hg_to_git_spaces(bookmark))

        # list the tags
        for tag, node in self.repo.tagslist():
            if tag != "tip":
                output("? refs/tags/%s" % hg_to_git_spaces(tag))

        output()

    def do_import(self, parser):
        HGImporter(self, parser).process()

    def do_export(self, parser):
        GitExporter(self, parser).process()


class HGImporter(object):
    '''A processor when the remote receives a git-remote import command.
    Provides import information from the mercurial repository to git.'''
    def __init__(self, hgremote, parser):
        self.hgremote = hgremote
        self.marks = self.hgremote.marks
        self.prefix = self.hgremote.prefix
        self.repo = self.hgremote.repo
        self.parser = parser
        self.notes_committed = 0

    def process(self):
        output("feature done")
        if self.hgremote.marks_git_path.exists():
            output("feature import-marks=%s" % self.hgremote.marks_git_path)
        output("feature export-marks=%s" % self.hgremote.marks_git_path)
        output("feature notes")
        actual_stdout.flush()

        tmp = encoding.encoding
        encoding.encoding = 'utf-8'

        self.commit_count = 0
        while self.parser.line.startswith('import'):
            ref = self.parser.line.split()[1]

            if ref == 'HEAD':
                self.process_ref(
                    self.hgremote.headnode[0],
                    'bookmarks',
                    self.hgremote.headnode[1])
            elif ref == 'refs/heads/master':
                self.do_branch('default')
            elif ref.startswith('refs/heads/branches/'):
                self.do_branch(ref[len('refs/heads/branches/'):])
            elif ref.startswith('refs/heads/'):
                bookmark = ref[len('refs/heads/'):]
                self.process_ref(bookmark,
                    'bookmarks',
                    self.hgremote.bookmarks[git_to_hg_spaces(bookmark)])
            elif ref.startswith('refs/tags/'):
                tag = ref[len('refs/tags/'):]
                self.process_ref(tag, 'tags', self.repo[git_to_hg_spaces(tag)])

            self.process_notes()

            self.parser.read_line()

        encoding.encoding = tmp
        output('done')

    def do_branch(self, branch):
        branch = git_to_hg_spaces(branch)
        try:
            heads = self.hgremote.branches[branch]
            if len(heads) > 1:
                log("Branch '%s' has more than one head, consider merging" % branch, "WARNING")
                tip = branch_tip(self.repo, branch)
            else:
                tip = heads[0]

        except KeyError:
            return

        head = self.repo[tip]
        self.process_ref(hg_to_git_spaces(branch), 'branches', head)

    def process_notes(self):
        last_notes_mark = self.marks.notes_mark if self.marks.notes_mark is not None else 0
        mark_to_hgsha1 = [(mark, self.repo[rev].hex()) for rev, mark in
                          self.marks.revisions_to_marks.iteritems() if mark > last_notes_mark]
        if not mark_to_hgsha1 or self.commit_count < 1:
            return
        output("commit refs/notes/hg-%s" % (self.hgremote.uuid))
        output("mark :%d" % (self.marks.new_notes_mark()))
        output("committer <gitifyhg-note> %s" % (strftime('%s %z')))
        message = u"hg from %s (%s)\n" % (self.prefix, self.hgremote.url)
        message = message.encode("utf-8")
        output("data %d" % (len(message)))
        output(message)
        if last_notes_mark > 0:
            output("from :%d" % (last_notes_mark))
        for mark, hgsha1 in mark_to_hgsha1:
            output("N inline :%d" % (mark))
            output("data 40")
            output(hgsha1)
        output()

    def process_ref(self, name, kind, head):

        # FIXME: I really need a better variable name here.
        kind_name = "%s/%s" % (kind, name)
        if kind_name == "branches/default":
            # I have no idea where 'bookmarks' comes from in this case.
            # I don't think there is meant to be many bookmarks/master ref,
            # but this is what I had to do to make tests pass when special
            # casing the master/default dichotomy. Something is still fishy
            # here, but it's less fishy than it was. See issue #34.
            kind_name = "bookmarks/master"
        tip = self.marks.tips.get(kind_name, 0)

        revs = xrange(tip, head.rev() + 1)
        count = 0

        for rev in revs:
            if self.marks.is_marked(rev):
                continue

            (manifest, user, (time, tz), files, description, extra
                ) = self.repo.changelog.read(self.repo[rev].node())

            user = sanitize_author(user)
            author = "%s %d %s" % (user, time, gittz(tz))

            if 'committer' in extra:
                user, time, tz = extra['committer'].rsplit(' ', 2)
                user = sanitize_author(user)
                committer = "%s %s %s" % (user, time, gittz(int(tz)))
            else:
                committer = author

            parents = [p for p in self.repo.changelog.parentrevs(rev) if p >= 0]

            if parents:
                modified, removed = self.get_filechanges(self.repo[rev],
                    parents[0])
            else:
                modified, removed = self.repo[rev].manifest().keys(), []

            if not parents and rev:
                output('reset %s/%s' % (self.prefix, kind_name))

            output("commit %s/%s" % (self.prefix, kind_name))
            output("mark :%d" % (self.marks.get_mark(rev)))
            output("author %s" % (author))
            output("committer %s" % (committer))
            output("data %d" % (len(description)))
            output(description)

            if parents:
                output("from :%s" % (self.marks.revision_to_mark(parents[0])))
                if len(parents) > 1:
                    output("merge :%s" % (self.marks.revision_to_mark(parents[1])))

            for file in modified:
                filecontext = self.repo[rev].filectx(file)
                data = filecontext.data()
                output("M %s inline %s" % (
                    gitmode(filecontext.flags()), filecontext.path()))
                output("data %d" % len(data))
                output(data)
            for file in removed:
                output("D %s" % (file))
            output()

            count += 1
            if (count % 100 == 0):
                output("progress revision %d '%s' (%d/%d)" % (
                    rev, name, count, len(revs)))
                output("#############################################################")

        # make sure the ref is updated
        output("reset %s/%s" % (self.prefix, kind_name))
        output("from :%u" % self.marks.revision_to_mark(head.rev()))
        output()

        self.marks.tips[kind_name] = head.rev()
        self.commit_count += count

    def get_filechanges(self, context, parent):
        modified = set()
        added = set()
        removed = set()

        current = context.manifest()
        previous = self.repo[parent].manifest().copy()

        for fn in current:
            if fn in previous:
                if (current.flags(fn) != previous.flags(fn) or current[fn] != previous[fn]):
                    modified.add(fn)
                del previous[fn]
            else:
                added.add(fn)
        removed |= set(previous.keys())

        return added | modified, removed


class GitExporter(object):
    '''A processor when the remote receives a git-remote `export` command.
    Provides export information to push commits from git to the mercurial
    repository.'''

    NULL_PARENT = '\0' * 20

    def __init__(self, hgremote, parser):
        self.hgremote = hgremote
        self.marks = self.hgremote.marks
        self.parsed_refs = self.hgremote.parsed_refs
        self.parsed_tags = {}  # refs to tuple of (message, author)
        self.blob_marks = self.hgremote.blob_marks
        self.repo = self.hgremote.repo
        self.parser = parser
        self.processed_marks = set()
        self.processed_nodes = []

    def process(self):
        self.marks.store()  # checkpoint
        new_branch = False
        self.parser.read_line()
        for line in self.parser.read_block('done'):
            command = line.split()[0]
            if command not in ('blob', 'commit', 'reset', 'tag', 'feature'):
                die('unhandled command: %s' % line)
            getattr(self, 'do_%s' % command)()

        for ref, node in self.parsed_refs.iteritems():
            if ref.startswith('refs/heads/branches'):
                branch = ref[len('refs/heads/branches'):]
                if git_to_hg_spaces(branch) not in self.hgremote.branches:
                    new_branch = True
            elif ref.startswith('refs/heads/'):
                bookmark = ref[len('refs/heads/'):]
                old = self.hgremote.bookmarks.get(bookmark)
                old = old.hex() if old else ''
                if not pushbookmark(self.repo, bookmark, old, node):
                    continue
            elif ref.startswith('refs/tags/'):
                self.write_tag(ref)
            else:
                # transport-helper/fast-export bugs
                log("Fast-export unexpected ref: %s" % ref, "WARNING")
                continue

        success = False
        try:
            self.repo.push(self.hgremote.peer, force=False, newbranch=new_branch)
            self.marks.store()
            success = True
        except Abort as e:
            # mercurial.error.Abort: push creates new remote head f14531ca4e2d!
            if e.message.startswith("push creates new remote head"):
                self.marks.load()  # restore from checkpoint
                # strip revs, implementation finds min revision from list
                if self.processed_nodes:
                    self.repo.mq.strip(self.repo, self.processed_nodes)
            else:
                die("unknown hg exception: %s" % e)
        # TODO: handle network/other errors?

        for ref in self.parsed_refs:
            if success:
                output("ok %s" % ref)
            else:
                output("error %s non-fast forward" % ref)  # TODO: other errors as well
        output()

        if not success:
            # wait until fast-export finishes to muck with the marks file
            self.remove_processed_git_marks()

    def remove_processed_git_marks(self):
        with self.hgremote.marks_git_path.open() as fread:
            with self.hgremote.marks_git_path.open('r+') as fwrite:
                for line in fread:
                    if not line.startswith(':'):
                        die("invalid line in marks-git: " + line)
                    mark = line[1:].split()[0]
                    if mark not in self.processed_marks:
                        fwrite.write(line)
                fwrite.truncate()

    def do_blob(self):
        mark = self.parser.read_mark()
        self.blob_marks[mark] = self.parser.read_data()
        self.parser.read_line()

    def do_reset(self):
        ref = self.parser.line.split()[1]

        # If the next line is a commit, allow it to process normally
        if not self.parser.peek().startswith('from'):
            return

        from_mark = self.parser.read_mark()
        from_revision = self.marks.mark_to_revision(from_mark)
        self.parsed_refs[ref] = self.repo.changelog.node(int(from_revision))

        # skip a line
        self.parser.read_line()

    def do_commit(self):
        files = {}
        extra = {}
        from_mark = merge_mark = None

        ref = self.parser.line.split()[1]

        commit_mark = self.parser.read_mark()
        author = self.parser.read_author()
        committer = self.parser.read_author()
        data = self.parser.read_data()
        if self.parser.peek().startswith('from'):
            from_mark = self.parser.read_mark()
        if self.parser.peek().startswith('merge'):
            merge_mark = self.parser.read_mark()
            if self.parser.peek().startswith('merge'):
                die('Octopus merges are not yet supported')

        self.parser.read_line()

        for line in self.parser.read_block(''):
            if line.startswith('M'):
                t, mode, mark_ref, path = line.split(' ', 3)
                mark = int(mark_ref[1:])
                filespec = {'mode': hgmode(mode), 'data': self.blob_marks[mark]}
            elif line.startswith('D'):
                t, path = line.split()
                filespec = {'deleted': True}
            files[path] = filespec

        user, date, tz = author

        if committer != author:
            extra['committer'] = "%s %u %u" % committer

        if from_mark:
            parent_from = self.repo.changelog.node(
                self.marks.mark_to_revision(from_mark))
        else:
            parent_from = self.NULL_PARENT

        if merge_mark:
            parent_merge = self.repo.changelog.node(
                self.marks.mark_to_revision(merge_mark))
        else:
            parent_merge = self.NULL_PARENT

        # hg needs to know about files that changed from either parent
        # whereas git only cares if it changed from the first parent.
        if merge_mark:
            for file in self.repo[parent_from].files():
                if file not in files and file in\
                        self.repo[parent_from].manifest():
                    files[file] = {'ctx': self.repo[parent_from][file]}

        if ref.startswith('refs/heads/branches/'):
            extra['branch'] = git_to_hg_spaces(
                ref[len('refs/heads/branches/'):])

        def get_filectx(repo, memctx, file):
            filespec = files[file]
            if 'deleted' in filespec:
                raise IOError
            if 'ctx' in filespec:
                return filespec['ctx']
            is_exec = filespec['mode'] == 'x'
            is_link = filespec['mode'] == 'l'
            rename = filespec.get('rename', None)
            return memfilectx(file, filespec['data'],
                    is_link, is_exec, rename)

        ctx = memctx(self.repo, (parent_from, parent_merge), data,
            files.keys(), get_filectx, user, (date, tz), extra)

        tmp = encoding.encoding
        encoding.encoding = 'utf-8'
        node = self.repo.commitctx(ctx)
        encoding.encoding = tmp

        rev = self.repo[node].rev()

        self.parsed_refs[ref] = node
        self.marks.new_mark(rev, commit_mark)
        self.processed_marks.add(str(commit_mark))
        self.processed_nodes.append(node)

    def do_tag(self):
        name = self.parser.line.split()[1]
        self.parser.read_mark()
        tagger = self.parser.read_author()
        message = self.parser.read_data()
        self.parser.read_line()
        self.parsed_tags[git_to_hg_spaces(name)] = tagger, message

    def do_feature(self):
        pass  # Ignore

    def write_tag(self, ref):
        node = self.parsed_refs[ref]
        tag = git_to_hg_spaces(ref[len('refs/tags/'):])
        branch = self.repo[node].branch()
        # Calling self.repo.tag() doesn't append the tag to the correct
        # commit. So I copied some of localrepo._tag into here.
        # But that method, like much of mercurial's code, is ugly.
        # So I then rewrote it.

        tags_revision = revsingle(self.repo, branch_tip(self.repo, branch))
        if '.hgtags' in tags_revision:
            old_tags = tags_revision['.hgtags'].data()
        else:
            old_tags = ''
        newtags = [old_tags]
        if old_tags and old_tags[-1] != '\n':
            newtags.append('\n')

        encoded_tag = encoding.fromlocal(tag)
        tag_line = '%s %s' % (hghex(node), encoded_tag)
        if tag_line in old_tags:
            return  # Don't commit a tag that was previously committed
        newtags.append(tag_line)

        def get_filectx(repo, memctx, file):
            return memfilectx(file, ''.join(newtags))

        if tag in self.parsed_tags:
            author, message = self.parsed_tags[tag]
            user, date, tz = author
            date_tz = (date, tz)
        else:
            message = "Added tag %s for changeset %s" % (tag, hgshort(node))
            user = None
            date_tz = None
        ctx = memctx(self.repo,
            (branch_tip(self.repo, branch), self.NULL_PARENT), message,
            ['.hgtags'], get_filectx, user, date_tz, {'branch': branch})

        tmp = encoding.encoding
        encoding.encoding = 'utf-8'
        node = self.repo.commitctx(ctx)
        encoding.encoding = tmp


def main():
    '''Main entry point for the git-remote-gitifyhg command. Parses sys.argv
    and constructs a parser from the result.
    '''
    HGRemote(*[x.decode('utf-8') for x in sys.argv[1:3]]).process()
    try:
        sys.stderr.close()
    except:
        pass


if __name__ == '__main__':
    sys.exit(main())
