#!/bin/sh

. ./sharness.sh

export DEBUG_GITIFYHG=on
export GIT_PAGER=cat
export HGRCPATH=''  # So extensions like pager don't interfere
export NL='
'

make_hg_repo() {
    mkdir hg_base &&
    cd hg_base &&
    hg init &&
    echo 'a\n' >> test_file &&
    hg add test_file &&
    hg commit --message="a" &&
    cd ..
}

make_hg_commit() {
    echo "$1" >> $2 &&
    hg commit -m "$1"
}

