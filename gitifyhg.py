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
from path import path as p

from mercurial.ui import ui
from mercurial import encoding
from mercurial.bookmarks import listbookmarks, readcurrent
from mercurial.util import sha1
from mercurial import hg


def log(msg, level="DEBUG", *args):
    sys.stderr.write('%s: %s\n' % (level, str(msg) % args))


def die(msg, *args):
    log(msg, 'ERROR', *args)
    sys.exit(1)


class GitRemoteParser(object):
    '''Parser for stdin that processes the git-remote protocol.'''

    def __init__(self, hgrepo):
        '''
        :param hgrepo: The mercurial repository object that contains the actual
            upstream remote that the parser needs to import and export from/to.
        '''
        self.hgrepo = hgrepo
        self.read_line()

    def read_line(self):
        '''Read a line from the standard input.'''
        self.line = sys.stdin.readline().strip()
        return self.line

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
        parser = GitRemoteParser(self.repo)

        for line in parser:
            command = line.split()[0]
            if command not in ('capabilities', 'list', 'import', 'export'):
                die('unhandled command: %s' % line)
            getattr(self, 'do_%s' % command)(parser)
            sys.stdout.flush()

    def do_capabilities(self, parser):
        '''Process the capabilities request when incoming from git-remote.
        '''
        print "import"
        print "export"
        print "refspec refs/heads/branches/*:%s/branches/*" % self.prefix
        print "refspec refs/heads/*:%s/bookmarks/*" % self.prefix
        print "refspec refs/tags/*:%s/tags/*" % self.prefix

        if self.marks_git_path.exists():
            print "*import-marks %s" % self.marks_git_path
        print "*export-marks %s" % self.marks_git_path

        print

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
        print "@refs/heads/%s HEAD" % self.headnode[0]

        # list the named branch references
        for branch in self.branches:
            print "? refs/heads/branches/%s" % branch

        # list the bookmark references
        for bookmark in self.bookmarks:
            print "? refs/heads/%s" % bookmark

        # list the tags
        for tag, node in self.repo.tagslist():
            if tag != "tip":
                print "? refs/tags/%s" % tag

        print

    def do_import(self, parser):
        HGImporter(self, parser).process()


class HGImporter(object):
    '''A processor when the remote receives a git-remote import command.
    Provides import information from the mercurial repository to git.'''
    def __init__(self, hgremote, parser):
        self.hgremote = hgremote
        self.parser = parser

    def process(self):
        print "feature done"
        if self.hgremote.marks_git_path.exists():
            print "feature import-marks=%s" % self.hgremote.marks_git_path
        print "feature export-marks=%s" % self.hgremote.marks_git_path
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
                branch = ref[len('refs/heads/branches/'):]
                self.do_branch(branch)  # FIXME: Call process_ref directly
            elif ref.startswith('refs/heads/'):
                bmark = ref[len('refs/heads/'):]
                self.do_bookmark(bmark)  # FIXME: Call process_ref directly
            elif ref.startswith('refs/tags/'):
                tag = ref[len('refs/tags/'):]
                self.do_tag(tag)  # FIXME: Call process_ref directly

            self.parser.read_line()

        encoding.encoding = tmp
        print 'done'

    def process_ref(self, name, kind, head):
        pass


def main():
    '''Main entry point for the git-remote-gitifyhg command. Parses sys.argv
    and constructs a parser from the result.
    '''
    HGRemote(*sys.argv[1:3]).process()


if __name__ == '__main__':
    sys.exit(main())
