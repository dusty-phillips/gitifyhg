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
from path import path as p

from mercurial.ui import ui
from mercurial import encoding
from mercurial.bookmarks import listbookmarks, readcurrent
from mercurial.util import sha1
from mercurial import hg


def log(msg, level="DEBUG"):
    sys.stderr.write('%s: %s\n' % (level, str(msg)))


def die(msg, *args):
    log(msg, 'ERROR', *args)
    sys.exit(1)


def output(msg=''):
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
            self.marks_to_revisions = {int(v): k for k, v in
                    self.marks_to_revisions.iteritems()}
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
        '''Returns an integer'''
        return self.marks_to_revisions[mark]

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
        log("PEEK: %s" % line)
        self.peek_stack.append(line)
        return line

    def read_mark(self):
        '''The remote protocol contains lines of the format mark: number.
        Return the mark.'''
        return self.line.partition(':')[-1]

    def read_data(self):
        '''Read all data following a data line for the given number of bytes'''
        if not self.line.startswith('data'):
            return None
        size = int(self.linepartition(':')[-1])
        return sys.stdin.read(size)

    def read_block(self, sentinel):
        '''Yield a block of lines one by one until the sentinel value
        is returned. Sentinel may be an empty string, 'done', or other values
        depending on what block is being read.'''
        while self.line != sentinel:
            yield self.line
            self.line = self.read_line()

    def __iter__(self):
        '''Loop over lines in a single block.'''
        return self.read_block('')


class HGRemote(object):
    def __init__(self, alias, url):
        gitdir = p(os.environ['GIT_DIR'])
        self.remotedir = gitdir.joinpath('hg', alias)
        self.marks_git_path = self.remotedir.joinpath('marks-git')
        self.marks = HGMarks(self.remotedir.joinpath('marks-hg'))
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

        local_path = os.path.join(self.remotedir, 'clone')
        if not os.path.exists(local_path):
            self.peer, dstpeer = hg.clone(myui, {}, url,
                local_path, update=False, pull=True)
            self.repo = dstpeer.local()
        else:
            self.repo = hg.repository(myui, local_path)
            self.peer = hg.peer(myui, {}, url)
            self.repo.pull(self.peer, heads=None, force=True)

    def process(self):
        '''Process the messages coming in on stdin using the git-remote
        protocol and respond appropriately'''
        parser = GitRemoteParser()

        for line in parser:
            command = line.split()[0]
            if command not in ('capabilities', 'list', 'import', 'export'):
                die('unhandled command: %s' % line)
            getattr(self, 'do_%s' % command)(parser)
            sys.stdout.flush()

    def do_capabilities(self, parser):
        '''Process the capabilities request when incoming from git-remote.
        '''
        output("import")
        output("export")
        output("refspec refs/heads/branches/*:%s/branches/*" % self.prefix)
        output("refspec refs/heads/*:%s/bookmarks/*" % self.prefix)
        output("refspec refs/tags/*:%s/tags/*" % self.prefix)

        if self.marks_git_path.exists():
            output("*import-marks %s" % self.marks_git_path)
        output("*export-marks %s" % self.marks_git_path)

        output()

    def do_list(self, parser):
        '''List all references in the mercurial repository. This includes
        the current head, all branches, and bookmarks.'''

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
                self.branches[branch] = heads  # FIXME: will it fail for multiple anonymous branches on a named branch?

        # list the head reference
        output("@refs/heads/%s HEAD" % self.headnode[0])

        # list the named branch references
        for branch in self.branches:
            output("? refs/heads/branches/%s" % branch)

        # list the bookmark references
        for bookmark in self.bookmarks:
            output("? refs/heads/%s" % bookmark)

        # list the tags
        for tag, node in self.repo.tagslist():
            if tag != "tip":
                output("? refs/tags/%s" % tag)

        output()

    def do_import(self, parser):
        HGImporter(self, parser).process()


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
                    self.hgremote.bookmarks[bookmark])
            elif ref.startswith('refs/tags/'):
                tag = ref[len('refs/tags/'):]
                self.process_ref(tag, 'tags', self.repo[tag])

            self.parser.read_line()

        encoding.encoding = tmp
        output('done')

    def do_branch(self, branch):
        try:
            heads = self.hgremote.branches[branch]
        except KeyError:
            tip = None

        if len(heads) > 1:
            log("Branch '%s' has more than one head, consider merging", "WARNING", branch)
            tip = self.repo.branchtip(branch)
        else:
            tip = heads[0]

        head = self.repo[tip]
        self.process_ref(branch, 'branches', head)

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

            rev_branch = extra['branch']

            author = "%s %d %s" % (user, time, gittz(tz))

            if 'committer' in extra:
                user, time, tz = extra['committer'].rsplit(' ', 2)
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


def main():
    '''Main entry point for the git-remote-gitifyhg command. Parses sys.argv
    and constructs a parser from the result.
    '''
    HGRemote(*sys.argv[1:3]).process()


if __name__ == '__main__':
    sys.exit(main())
