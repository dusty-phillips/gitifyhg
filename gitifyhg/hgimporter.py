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

import time
import re

from mercurial import encoding

from .util import (log, output, actual_stdout, gittz, gitmode,
    git_to_hg_spaces, hg_to_git_spaces, branch_tip, ref_to_name_kind,
    make_kind_name)

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
            else:
                name, kind = ref_to_name_kind(ref)
                if kind == 'branches':
                    head = self.branch_head(name)
                elif kind == 'bookmarks':
                    head = self.hgremote.bookmarks[git_to_hg_spaces(name)]
                elif kind == 'tags':
                    head = self.repo[git_to_hg_spaces(name)]
                else:
                    assert False, "unexpected kind: %s" % kind
                self.process_ref(name, kind, head)

            self.process_notes()

            self.parser.read_line()

        encoding.encoding = tmp
        output('done')

    def branch_head(self, branch):
        branch = git_to_hg_spaces(branch)
        try:
            heads = self.hgremote.branches[branch]
            if len(heads) > 1:
                log("Branch '%s' has more than one head, consider merging" % (
                    branch), "WARNING")
                tip = branch_tip(self.repo, branch)
            else:
                tip = heads[0]

        except KeyError:
            return

        return self.repo[tip]

    def process_notes(self):
        last_notes_mark = self.marks.notes_mark if self.marks.notes_mark is not None else 0
        mark_to_hgsha1 = [(mark, self.repo[rev].hex()) for rev, mark in
                          self.marks.revisions_to_marks.iteritems() if mark > last_notes_mark]
        if not mark_to_hgsha1 or self.commit_count < 1:
            return
        output("commit refs/notes/hg-%s" % (self.hgremote.uuid))
        output("mark :%d" % (self.marks.new_notes_mark()))
        output("committer <gitifyhg-note> %s" % (time.strftime('%s %z')))
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
        kind_name = make_kind_name(kind, name)
        tip = self.marks.tips.get(kind_name, 0)

        revs = xrange(tip, head.rev() + 1)
        count = 0

        for rev in revs:
            node = self.repo[rev].node()
            if self.marks.is_marked(node):
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
            output("mark :%d" % (self.marks.get_mark(node)))
            output("author %s" % (author))
            output("committer %s" % (committer))
            output("data %d" % (len(description)))
            output(description)

            if parents:
                output("from :%s" % (self.marks.revision_to_mark(self.repo[parents[0]].node())))
                if len(parents) > 1:
                    output("merge :%s" % (self.marks.revision_to_mark(self.repo[parents[1]].node())))

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
        output("from :%u" % self.marks.revision_to_mark(head.node()))
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
