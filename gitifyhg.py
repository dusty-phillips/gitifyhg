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
import re
import json

import sh
from path import path as p
from six.moves import configparser


class GitifyHGError(Exception):
    pass


def clone(hg_url, dir=None, branch_name="default"):
    '''Set up a new git repository that is subconsciously linked to the hg
    repository in the hg_url. The link uses an intermediate 'patches' directory
    where patches are stored as input to/from git am/format_patch
    and hg import/export. Once cloned the state of the master branch will be
    the same as the state of the upstream tip for the chosen branch
    (defaults to branch_name).

    It is only possible to follow one upstream branch. Normally this will be
    ``default``. If you need to work on a different branch, you'll need to
    reclone the repository.

    :param hg_url: the mercurial repository to clone from
    :param dir: the optional path to clone into. If not specified, the dir is
        set to the basename of the hg_url.
    :param branch_name: the name of the upstream branch you want to follow'''
    if dir is not None:
        git_repo = p(dir).abspath()
    else:
        git_repo = p(hg_url.split('/')[-1]).abspath()
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

    hg_export(patches,
        "ancestors(min(branch({0}))) or branch({0})".format(branch_name))
    sh.cd(git_repo)
    sh.git.init()
    sh.git.config('alias.hgrebase', '!gitifyhg rebase')
    sh.git.config('alias.hgpush', '!gitifyhg push')
    git_import(patches)
    sh.git.branch('hg{0}'.format(branch_name))  # last commit from upstream
    with open('.gitignore', 'w') as gitignore:
        gitignore.write('.gitignore\n')
        gitignore.write('.gitifyhg')
    with open('.gitifyhg/config.json', 'w') as file:
        json.dump({'upstream_branch': branch_name}, file)

    empty_directory(patches)


def rebase():
    '''If commits have happened in the upstream hg default branch, rebase
    master onto those commits. This method assumes that gitifyhg created the
    current git repository, and therefore a .gitifyhg/hg_clone exists.'''

    with open('.gitifyhg/config.json') as file:
        upstream_branch = json.load(file)['upstream_branch']

    git_dir = p('.').abspath()
    patches = git_dir.joinpath('.gitifyhg/patches')
    sh.cd('.gitifyhg/hg_clone')
    last_pulled_commit = sh.grep(sh.hg.log(rev=upstream_branch), 'changeset').stdout
    last_pulled_commit = int(re.match(
        b'changeset:\s+(\d+):', last_pulled_commit).groups()[0])
    sh.hg.pull(update=True)
    hg_export(patches, "{0}:{1} and branch({1})".format(
        last_pulled_commit + 1, upstream_branch))
    sh.git.checkout('hg{0}'.format(upstream_branch))
    git_import(patches)
    sh.git.checkout('master')
    sh.git.rebase('hg{0}'.format(upstream_branch))
    empty_directory(patches)


def push():
    '''If commits have not happened upstream hg repo, but they have happened
    in the local master, push the new commits to upstream.'''
    with open('.gitifyhg/config.json') as file:
        upstream_branch = json.load(file)['upstream_branch']

    git_dir = p('.').abspath()
    patches = git_dir.joinpath('.gitifyhg/patches')
    hg_clone = git_dir.joinpath('.gitifyhg/hg_clone')
    sh.cd(hg_clone)
    try:
        sh.hg.incoming()
    except sh.ErrorReturnCode:
        # Raises an exception when there are NO incoming patches, so we invert
        # the exception in else
        pass
    else:
        raise GitifyHGError("Refusing to push: upstream changes. Rebase first")

    sh.cd(git_dir)
    sh.git('format-patch', 'hg{0}..master'.format(upstream_branch),
        output_directory=patches)
    sh.cd(hg_clone)
    hg_import(patches)
    sh.hg.push()
    sh.cd(git_dir)
    sh.git.checkout('hg{0}'.format(upstream_branch))
    sh.git.merge('master')
    sh.git.checkout('master')
    empty_directory(patches)


# HELPERS
def hg_export(patch_directory, revision_spec):
    '''Export all patches matching the given mercurial revspec into the
    patches directory.'''
    sh.hg.export(git=True, output=patch_directory.joinpath('%R.patch'),
        rev=revision_spec)


def hg_import(patch_directory):
    '''Import all patches in the patch_directory onto the current branch in
    hg'''
    patch_files = [patch_directory.joinpath(patch) for patch in
        sorted(patch_directory.listdir()) if patch.endswith('.patch')]
    sh.hg('import', patch_files)


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
    if sys.argv[1] in ('clone', 'rebase', 'push'):
        globals()[sys.argv[1]](*sys.argv[2:])

if __name__ == '__main__':
    main()
