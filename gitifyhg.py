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


def clone(hg_url):
    '''Set up a new git repository that is subconsciously linked to the hg
    repository in the hg_url. The link uses an intermediate 'patches' directory
    where patches are stored as input to/from git am/format_patch
    and hg import/export.'''
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
    sh.hg.export(git=True, output=patches.joinpath('%R.patch'),
        rev="branch(default)")
    sh.cd(git_repo)
    sh.git.init()
    patch_files = [patches.joinpath(patch) for patch in
        sorted(patches.listdir()) if patch.endswith('.patch')]
    sh.git.am(*patch_files)
    sh.git.branch('hgrepo')
    with open('.gitignore', 'w') as gitignore:
        gitignore.write('.gitignore\n')
        gitignore.write('.gitifyhg')

    for file in patches.listdir():
        patches.joinpath(file).remove()


def main():
    if sys.argv[1] in ('clone'):
        globals()[sys.argv[1]](*sys.argv[1:])

if __name__ == '__main__':
    main()
