#!/bin/sh

. ./sharness.sh

export DEBUG_GITIFYHG=on
export GIT_PAGER=cat
export HGRCPATH=''  # So extensions like pager don't interfere
export NL='
'

make_hg_repo() {
    mkdir hg_repo &&
    cd hg_repo &&
    hg init &&
    echo 'a\n' >> test_file &&
    hg add test_file &&
    hg commit --message="a"
}

clone_repo() {
    test_expect_code 0 git clone testgitifyhg::hg_repo git_clone &&
    cd git_clone
}

make_hg_commit() {
    echo "$1" >> $2 &&
    hg add $2 &&
    hg commit -m "$1"
}

assert_git_messages() {
    test "`git log --pretty=format:%B`" = "$1"
}
