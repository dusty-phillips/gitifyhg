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
# along with gitifyhg.  If not, see <http://www.gnu.org/licenses/>.import sh


import sys
import sh
from path import path as p
from six.moves import configparser


def clone(hg_url):
    '''Set up a new git repository that is subconsciously linked to the hg
    repository in the hg_url. The link uses an intermediate 'patches' directory
    where patches are stored as input to/from git am/format_patch
    and hg import/export. Once cloned the state of the master branch will be
    the same as the state of the upstream default tip. However, the history
    may not be identical, since merged branches are ignored.'''
    repo_name = hg_url.split('/')[-1]
    git_repo = p(repo_name).abspath()
    git_repo.mkdir()
    gitify_hg = git_repo.joinpath('.gitifyhg')
    gitify_hg.mkdir()
    patches = gitify_hg.joinpath('patches')
    patches.mkdir()
    hg_repo = gitify_hg.joinpath('hg_clone')
    sh.cd(gitify_hg)
    sh.hg.clone(hg_url, hg_repo)
    sh.cd(hg_repo)

    # Disable colored output in all hg commands.
    hgconfig = configparser.ConfigParser()
    hgconfig.read('.hg/hgrc')
    hgconfig.add_section('color')
    hgconfig.set('color', 'mode', 'off')
    with open('.hg/hgrc', 'w') as file:
        hgconfig.write(file)

    hg_export(patches, "branch(default)")
    sh.cd(git_repo)
    sh.git.init()
    git_import(patches)
    sh.git.branch('hgrepo')  # hgrepo points at last commit pulled from upstream
    with open('.gitignore', 'w') as gitignore:
        gitignore.write('.gitignore\n')
        gitignore.write('.gitifyhg')

    empty_directory(patches)


def rebase():
    '''If commits have happened in the upstream hg default branch, rebase
    master onto those commits. This method assumes that gitifyhg created the
    current git repository, and therefore a .gitifyhg/hg_clone exists.'''

    sh.cd('.gitifyhg/hg_clone')
    last_pulled_commit = sh.grep(sh.hg.log(rev='default'), 'changeset').stdout
    sh.hg.pull(update=True)
    print(last_pulled_commit)


# HELPERS
def hg_export(patch_directory, revision_spec):
    '''Export all patches matching the given mercurial revspec into the
    patches directory.'''
    sh.hg.export(git=True, output=patch_directory.joinpath('%R.patch'),
        rev=revision_spec)


def git_import(patch_directory):
    '''Import all patches in the patch_directory onto the current branch in
    git.'''
    patch_files = [patch_directory.joinpath(patch) for patch in
        sorted(patch_directory.listdir()) if patch.endswith('.patch')]
    sh.git.am(*patch_files)


def empty_directory(directory):
    for file in directory.listdir():
        directory.joinpath(file).remove()


# MAIN
def main():
    if sys.argv[1] in ('clone', 'rebase'):
        globals()[sys.argv[1]](*sys.argv[1:])

if __name__ == '__main__':
    main()
