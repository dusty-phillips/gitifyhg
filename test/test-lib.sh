#!/bin/sh

. ./sharness.sh

export GIT_AUTHOR_EMAIL=git.user@example.com
export GIT_AUTHOR_NAME='Git User'
export GIT_USER="$GIT_AUTHOR_NAME <$GIT_AUTHOR_EMAIL>"
export HG_USER="Hg User <hg.user@example.com>"
export DEBUG_GITIFYHG=on
export GIT_PAGER=cat
unset HGRCPATH      # Prevent user's environment from affecting hg command
export NL='
'

make_hg_repo() {
    mkdir hg_repo &&
    cd hg_repo &&
    hg init &&
    echo 'a\n' >> test_file &&
    hg add test_file &&
    hg commit --message="a" --user="$HG_USER"
}

clone_repo() {
    cd .. &&
    test_expect_code 0 git clone "testgitifyhg::hg_repo" git_clone &&
    cd git_clone &&
    git config user.email $GIT_AUTHOR_EMAIL &&
    git config user.name "$GIT_USER"
}

make_cloned_repo() {
    make_hg_repo &&
    clone_repo &&
    cd ../hg_repo
}

make_hg_commit() {
    if test $# -eq 3 ; then
        user=$3
    else
        user=$HG_USER
    fi
    echo "$1" >> $2 &&
    hg add $2 &&
    hg commit -m "$1" --user="$user"
}
make_git_commit() {
    echo "$1" >> "$2" &&
    git add "$2" &&
    git commit -m "$1"
}

assert_git_messages() {
    if test $# -eq 2 ; then
        test "`git log --pretty=format:%B $2`" = "$1"
    else
        test "`git log --pretty=format:%B`" = "$1"
    fi
}

assert_hg_messages() {
    if test $# -eq 2 ; then
        test "`hg log --template=\"{desc}\n\" -r $2`" = "$1"
    else
        test "`hg log --template=\"{desc}\n\"`" = "$1"
    fi
}

assert_hg_author() {
    if test $# -eq 2 ; then
        rev=$2
    else
        rev=tip
    fi
    test "`hg log --template='{author}' --rev=$rev`" = "$1"
}

assert_git_author() {
    if test $# -eq 2 ; then
        ref=$2
    else
        ref=HEAD
    fi
    test "`git show -s --format='%an <%ae>' $ref`" = "$1"
}
assert_git_count() {
    if test $# -eq 2 ; then
        ref=$2
    else
        ref=HEAD
    fi
    test `git rev-list $ref --count` -eq $1
}
assert_hg_count() {
    if test $# -eq 2 ; then
        rev=$2
    else
        rev=tip
    fi
    test `hg log -q -r 0:$rev | wc -l` -eq $1

}
assert_git_notes() {
    git notes --ref=hg merge $(basename $(ls .git/refs/notes/hg-*)) &&
    git log --pretty="format:%N" --notes='hg' | grep -v '^$'
    echo $1
    test "`git log --pretty="format:%N" --notes='hg' | grep -v '^$'`" = "$1"

}
