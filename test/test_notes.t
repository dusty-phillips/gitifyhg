#!/bin/sh

test_description='Test gitifyhg notes'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'basic clone with notes' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file &&
    hgsha1s=`hg log --template "{node}\n"` &&

    clone_repo &&

    assert_git_messages "b${NL}a" &&
    assert_git_notes "$hgsha1s" &&


    cd ..
'

test_expect_success 'basic pull with notes' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_cloned_repo &&
    make_hg_commit b test_file &&
    hgsha1s=`hg log --template "{node}\n"` &&

    cd ../git_clone &&
    git pull &&

    assert_git_messages "b${NL}a" &&
    assert_git_notes "$hgsha1s" &&

    cd ..
'

test_expect_success 'pull notes rename remote' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    cd .. &&
    mkdir git_clone &&
    cd git_clone &&
    git init &&
    git remote add --fetch the_remote gitifyhg::../hg_repo &&
    git pull the_remote master &&
    assert_git_messages "a" &&
    cd ../hg_repo &&
    make_hg_commit b test_file &&
    make_hg_commit c test_file &&
    cd ../git_clone &&
    git fetch the_remote &&
    assert_git_count 3 the_remote/master &&
    cd ../hg_repo &&
    make_hg_commit d test_file &&
    hgsha1s=`hg log --template "{node}\n"` &&

    cd ../git_clone &&
    git remote rename the_remote new_remote_name &&
    git pull new_remote_name master &&
    assert_git_messages "d${NL}c${NL}b${NL}a" &&
    assert_git_notes "$hgsha1s" &&

    cd ..
'

# see 30
test_expect_failure 'simple push updates notes' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    cd ../hg_repo &&
    hgsha1s=`hg log --template "{node}\n"` &&
    cd ../git_clone &&
    test_expect_code 0 git fetch &&
    assert_git_count 2 'origin' &&
    assert_git_notes $hgsha1s &&

    cd ..
'

test_expect_success 'simple push updates after pull' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    test_expect_code 0  git fetch &&
    cd ../hg_repo &&
    hg update &&
    make_hg_commit "c" test_file &&
    hgsha1s=`hg log --template "{node}\n"` &&
    cd ../git_clone &&
    git pull &&
    assert_git_count 3 &&
    assert_git_notes "$hgsha1s" &&

    cd ..
'

test_done
