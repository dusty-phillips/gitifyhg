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
    cd .. &&
    test_expect_code 0 git clone "testgitifyhg::hg_repo" git_clone &&
    cd git_clone &&
    git config user.email "you@example.com" &&
    git config user.name "Your Name"
}

make_hg_commit() {
    echo "$1" >> $2 &&
    hg add $2 &&
    hg commit -m "$1"
}
make_git_commit() {
    echo "$1" >> $2 &&
    git add $2 &&
    git commit -m "$1"
}

assert_git_messages() {
    test "`git log --pretty=format:%B`" = "$1"
}

assert_hg_messages() {
    if test $# -eq 2 ; then
        test "`hg log --template=\"{desc}\n\" -r $2`" = "$1"
    else
        test "`hg log --template=\"{desc}\n\"`" = "$1"
    fi
}
