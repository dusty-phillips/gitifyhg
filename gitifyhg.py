# Copyright 2012 Dusty Phillips

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

from mercurial.ui import ui
from mercurial.context import memctx, memfilectx
from mercurial import encoding
from mercurial.bookmarks import listbookmarks, readcurrent, pushbookmark
from mercurial.util import sha1
from mercurial import hg
from mercurial.error import RepoLookupError


DEBUG_GITIFYHG = os.environ.get("DEBUG_GITIFYHG", "").lower() == "on"


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
    print(msg)


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


AUTHOR = re.compile(r'^([^<>]+?)? ?<([^<>]*)>$')
NAME = re.compile(r'^([^<>]+)')


def sanitize_author(author):
    '''Mercurial allows a more freeform user string than git, so we have to
    massage it to be compatible. Git experts "name <email>".'''
    name = "unknown"
    email = "unknown"
    author = author.replace('"', '')
    match = AUTHOR.match(author)
    if match:
        name = match.group(1)
        email = match.group(2).strip()
    else:
        match = NAME.match(author)
        if match:
            if "@" in match.group(1):  # when they provide email without name
                email = match.group(1).strip()
            else:
                name = match.group(1).strip()

    return '%s <%s>' % (name, email)


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
        else:
            self.tips = {}
            self.revisions_to_marks = {}
            self.marks_to_revisions = {}
            self.last_mark = 0

    def store(self):
        '''Save marks to the storage file.'''
        with self.storage_path.open('w') as file:
            json.dump({
                'tips': self.tips,
                'revisions_to_marks': self.revisions_to_marks,
                'last-mark': self.last_mark},
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
        AUTHOR_RE = re.compile('^\w+ (?:(.+)? ?<.*>) (\d+) ([+-]\d+)')
        match = AUTHOR_RE.match(self.line)
        if not match:
            return None

        user, date, tz = match.groups()

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

        gitdir = p(os.environ['GIT_DIR'].decode('utf-8'))
        self.remotedir = gitdir.joinpath('hg', alias)
        self.marks_git_path = self.remotedir.joinpath('marks-git')
        self.marks = HGMarks(self.remotedir.joinpath('marks-hg'))
        self.parsed_refs = {}
        self.blob_marks = {}
        self.branches = {}
        self.bookmarks = {}

        if alias[8:] == url:  # strips off 'gitifyhg::'
            alias = sha1(alias).hexdigest()
        self.prefix = 'refs/hg/%s' % alias
        self.build_repo(url, alias)

    def build_repo(self, url, alias):
        '''Make the Mercurial repo object self.repo available. If the local
        clone does not exist, clone it, otherwise, ensure it is fetched.'''
        myui = ui()
        myui.setconfig('ui', 'interactive', 'off')

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
            sys.stdout.flush()

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
            node = self.repo['.'] or self.repo['tip']
            if not node:
                output()
                return
            head = head if head != 'default' else 'master'
            self.bookmarks[head] = node

        self.headnode = (head, node)

        # Update the bookmark references
        for bookmark, node in listbookmarks(self.repo).iteritems():
            self.bookmarks[bookmark] = self.repo[node]

        # update the named branch references
        for branch in self.repo.branchmap():
            heads = self.repo.branchheads(branch)
            if heads:
                self.branches[branch] = heads

        # list the head reference
        output("@refs/heads/%s HEAD" % self.headnode[0])

        # list the named branch references
        for branch in self.branches:
            output("? refs/heads/branches/%s" % hg_to_git_spaces(branch))

        # list the bookmark references
        for bookmark in self.bookmarks:
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

    def process(self):
        output("feature done")
        if self.hgremote.marks_git_path.exists():
            output("feature import-marks=%s" % self.hgremote.marks_git_path)
        output("feature export-marks=%s" % self.hgremote.marks_git_path)
        sys.stdout.flush()

        tmp = encoding.encoding
        encoding.encoding = 'utf-8'

        while self.parser.line.startswith('import'):
            ref = self.parser.line.split()[1]

            if (ref == 'HEAD'):
                self.process_ref(
                    self.hgremote.headnode[0],
                    'bookmarks',
                    self.hgremote.headnode[1])
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

            self.parser.read_line()

        encoding.encoding = tmp
        output('done')

    def do_branch(self, branch):
        branch = git_to_hg_spaces(branch)
        try:
            heads = self.hgremote.branches[branch]
            if len(heads) > 1:
                log("Branch '%s' has more than one head, consider merging" % branch, "WARNING")
                tip = self.repo.branchtip(branch)
            else:
                tip = heads[0]

        except KeyError:
            return

        head = self.repo[tip]
        self.process_ref(hg_to_git_spaces(branch), 'branches', head)

    def process_ref(self, name, kind, head):

        kind_name = "%s/%s" % (kind, name)
        tip = self.marks.tips.get(kind_name, 0)

        if tip and tip == head.rev():
            return  # shortcut for no changes

        revs = xrange(tip, head.rev() + 1)
        count = 0

        revs = [rev for rev in revs if not self.marks.is_marked(rev)]

        for rev in revs:
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
        output("from :%u" % self.marks.revision_to_mark(rev))
        output()

        self.marks.tips[kind_name] = rev

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
        self.blob_marks = self.hgremote.blob_marks
        self.repo = self.hgremote.repo
        self.parser = parser

    def process(self):
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
                tag = ref[len('refs/tags/'):]
                self.repo.tag([tag], node, None, True, None, {})
                # FIXME: the new tag needs to be committed in such a way that
                # the commit doesn't interfere with any other commits being
                # exported.
            else:
                # transport-helper/fast-export bugs
                continue
            output("ok %s" % ref)

        output()

        self.repo.push(self.hgremote.peer, force=False, newbranch=new_branch)

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
        # FIXME: This needs to be in it's own method or function somehow.
        #        The importer uses similar logic.
        if ref.startswith('refs/heads/branches/'):
            branch_name = ref[len('refs/heads/branches/'):]
            try:
                tip = self.repo.branchtip(git_to_hg_spaces(branch_name))
                git_marked_tip = self.marks.tips['branches/%s' % branch_name]
            except RepoLookupError:
                # setting these to 0 isn't honest, but it (currently)
                # only has to pass the if git_marked_tip < tip: below
                tip = git_marked_tip = 0
        elif ref == 'refs/heads/master':
            try:
                tip = self.repo.branchtip('default')
                git_marked_tip = self.marks.tips['bookmarks/master']
            except RepoLookupError:
                tip = git_marked_tip = 0
        elif ref.startswith('refs/heads/'):
            bookmark = ref[len('refs/heads/'):]
            tip = listbookmarks(self.repo)[git_to_hg_spaces(bookmark)]
            git_marked_tip = self.marks.tips['bookmarks/%s' % bookmark]

        tip = self.repo[tip].rev()
        log("%r %r" % (git_marked_tip, tip))
        if git_marked_tip < tip:
            output("error %s already exists\n" % ref)
            sys.exit(1)

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
            extra['branch'] = git_to_hg_spaces(branch_name)

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

    def do_tag(self):
        name = self.parser.line().split()[1]
        from_mark = self.parser.read_mark()
        tagger = self.parser.read_author()
        data = self.parser.read_data()

    def do_feature(self):
        pass  # Ignore


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
