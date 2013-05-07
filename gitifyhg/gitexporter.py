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

from mercurial.context import memctx, memfilectx
from mercurial import encoding
from mercurial.error import Abort
from mercurial.node import hex as hghex  # What idiot overroad a builtin?
from mercurial.node import short as hgshort
from mercurial.bookmarks import pushbookmark
from mercurial.scmutil import revsingle

from .util import (die, output, git_to_hg_spaces, hgmode, branch_tip,
    ref_to_name_reftype, BRANCH, BOOKMARK, TAG, user_config)


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
        self.hgrc = user_config()

    def process(self):
        self.marks.store()  # checkpoint
        new_branch = False
        push_bookmarks = []
        self.parser.read_line()
        for line in self.parser.read_block('done'):
            command = line.split()[0]
            if command not in ('blob', 'commit', 'reset', 'tag', 'feature'):
                die('unhandled command: %s' % line)
            getattr(self, 'do_%s' % command)()

        updated_refs = {}
        for ref, node in self.parsed_refs.iteritems():
            if ref.startswith(self.hgremote.prefix):
                # This seems to be a git fast-export bug
                continue
            name, reftype = ref_to_name_reftype(ref)
            name = git_to_hg_spaces(name)
            if reftype == BRANCH:
                if name not in self.hgremote.branches:
                    new_branch = True
            elif reftype == BOOKMARK:
                old = self.hgremote.bookmarks.get(name)
                old = old.hex() if old else ''
                if not pushbookmark(self.repo, name, old, node):
                    continue
                push_bookmarks.append((name, old, hghex(node)))
            elif reftype == TAG:
                self.write_tag(name, node)
            else:
                assert False, "unexpected reftype: %s" % reftype
            updated_refs[ref] = node

        success = False
        try:
            self.repo.push(self.hgremote.peer, force=False, newbranch=new_branch)
            for bookmark, old, new in push_bookmarks:
                self.hgremote.peer.pushkey('bookmarks', bookmark, old, new)
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

        for ref, node in updated_refs.items():
            if success:
                status = ""
                name, reftype = ref_to_name_reftype(ref)
                gitify_ref = self.hgremote.make_gitify_ref(name, reftype)
                last_known_rev = self.marks.tips.get(gitify_ref)
                new_rev = self.repo[node].rev()
                if last_known_rev is not None and last_known_rev == new_rev:
                    # up to date status tells git that nothing has changed
                    # during the push for this ref, which prevents it from
                    # printing pointless status info to the user such as:
                    #  * [new branch]      master -> master
                    status = " up to date"
                output("ok %s%s" % (ref, status))
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
        self.parsed_refs[ref] = from_revision

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
                t, path = line.split(' ', 1)
                filespec = {'deleted': True}
            if path.startswith('/"') and path.endswith('"') and ' ' in path:
                path = "/" + path[2:-2]
            files[path] = filespec

        user, date, tz = author

        if committer != author:
            extra['committer'] = "%s %u %u" % committer

        if from_mark:
            parent_from = self.marks.mark_to_revision(from_mark)
        else:
            parent_from = self.NULL_PARENT

        if merge_mark:
            parent_merge = self.marks.mark_to_revision(merge_mark)
        else:
            parent_merge = self.NULL_PARENT

        # hg needs to know about files that changed from either parent
        # whereas git only cares if it changed from the first parent.
        if merge_mark:
            for file in self.repo[parent_from].files():
                if file not in files and file in\
                        self.repo[parent_from].manifest():
                    files[file] = {'ctx': self.repo[parent_from][file]}

        name, reftype = ref_to_name_reftype(ref)
        if reftype == BRANCH:
            extra['branch'] = git_to_hg_spaces(name)

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

        self.parsed_refs[ref] = node
        self.marks.new_mark(node, commit_mark)
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

    def write_tag(self, name, node):
        branch = self.repo[node].branch()
        # Calling self.repo.tag() doesn't append the tag to the correct
        # commit. So I copied some of localrepo._tag into here.
        # But that method, like much of mercurial's code, is ugly.
        # So I then rewrote it.

        tags_revision = revsingle(self.repo, hghex(branch_tip(self.repo, branch)))
        if '.hgtags' in tags_revision:
            old_tags = tags_revision['.hgtags'].data()
        else:
            old_tags = ''
        newtags = [old_tags]
        if old_tags and old_tags[-1] != '\n':
            newtags.append('\n')

        encoded_tag = encoding.fromlocal(name)
        tag_line = '%s %s' % (hghex(node), encoded_tag)
        if tag_line in old_tags:
            return  # Don't commit a tag that was previously committed
        newtags.append(tag_line)

        def get_filectx(repo, memctx, file):
            return memfilectx(file, ''.join(newtags))

        if name in self.parsed_tags:
            author, message = self.parsed_tags[name]
            user, date, tz = author
            date_tz = (date, tz)
        else:
            message = "Added tag %s for changeset %s" % (name, hgshort(node))
            user = self.hgrc.get("ui", "username", None)
            date_tz = None  # XXX insert current date here
        ctx = memctx(self.repo,
            (branch_tip(self.repo, branch), self.NULL_PARENT), message,
            ['.hgtags'], get_filectx, user, date_tz, {'branch': branch})

        tmp = encoding.encoding
        encoding.encoding = 'utf-8'
        node = self.repo.commitctx(ctx)
        encoding.encoding = tmp
