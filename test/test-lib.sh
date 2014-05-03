#!/bin/sh

. ./sharness.sh

export GIT_AUTHOR_EMAIL=git.user@example.com
export GIT_AUTHOR_NAME='Git User'
export GIT_COMMITTER_EMAIL=git.user@example.com
export GIT_COMMITTER_NAME='Git User'
export GIT_USER="$GIT_AUTHOR_NAME <$GIT_AUTHOR_EMAIL>"
export HG_USER="Hg User <hg.user@example.com>"
export DEBUG_GITIFYHG=$debug
export GIT_PAGER=cat
export HGRCPATH="$HOME/.hgrc"
export NL='
'
export PYTHONPATH="$SHARNESS_BUILD_DIRECTORY"
export PATH="$SHARNESS_TEST_DIRECTORY:$PATH"

make_hg_repo() {
    hg init hg_repo &&
    cd hg_repo &&
    echo 'a\n' >> test_file &&
    hg add test_file &&
    hg commit --message="a" --user="$HG_USER"
}

clone_repo() {
    cd .. &&
    test_expect_code 0 git clone "gitifyhg::hg_repo" git_clone &&
    cd git_clone
}

make_cloned_repo() {
    make_hg_repo &&
    clone_repo &&
    cd ../hg_repo
}

make_hg_commit() {
    echo "$1" >> $2 &&
    hg add $2 &&
    hg commit -m "$1" --user="${3-$HG_USER}"
}

make_git_commit() {
    echo "$1" >> "$2" &&
    git add "$2" &&
    git commit -m "$1"
}

assert_git_messages() {
    test "`git log -z --pretty=format:%B ${2-}`" = "$1"
}

assert_hg_messages() {
    test "`hg log --template=\"{desc}\n\" ${2+-r $2}`" = "$1"
}

assert_hg_author() {
    test "`hg log --template='{author}' --rev=${2-tip}`" = "$1"
}

assert_git_author() {
    test "`git show -s --format='%an <%ae>' ${2-HEAD}`" = "$1"
}

assert_git_count() {
    test `git rev-list ${2-HEAD} --count` -eq $1
}

assert_hg_count() {
    test `hg log -q -r 0:${2-tip} | wc -l` -eq $1

}

assert_git_notes() {
    git notes --ref=hg merge $(basename $(ls .git/refs/notes/hg-*)) &&
    git log --pretty="format:%N" --notes='hg' | grep -v '^$' &&
    echo $1 &&
    test "`git log --pretty="format:%N" --notes='hg' | grep -v '^$'`" = "$1"
}
