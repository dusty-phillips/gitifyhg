#!/bin/sh

test_description='Test gitifyhg pull from hg'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'basic pull' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_cloned_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    git pull &&

    assert_git_messages "b${NL}a" &&
 
    cd ..
'

test_expect_success 'pull named remote' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    cd .. &&
    mkdir git_repo &&
    cd git_repo &&
    git init &&
    git remote add --fetch the_remote gitifyhg::../hg_repo
    git pull the_remote master &&
    assert_git_messages a &&
    cd ../hg_repo &&
    make_hg_commit b test_file &&
    make_hg_commit c test_file &&
    cd ../git_repo &&
    git fetch the_remote &&
    assert_git_messages "c${NL}b${NL}a" the_remote/master &&

    cd ../hg_repo &&
    make_hg_commit d test_file &&

    cd ../git_repo &&
    git remote rename the_remote new_remote_name &&
    git pull new_remote_name master &&
    assert_git_messages "d${NL}c${NL}b${NL}a" &&


    cd ..
'

test_expect_success 'pull from named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch feature &&
    make_hg_commit b test_file &&

    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit c test_file &&
    cd ../git_clone &&
    git checkout origin/branches/feature --track &&
    assert_git_messages "b${NL}a" &&
    git pull &&
    assert_git_messages "c${NL}b${NL}a" &&

    cd ..
'

test_expect_success 'pull conflict' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_cloned_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    make_git_commit c test_file &&

    git pull 2>&1 | grep "Automatic merge failed" &&

    cd ..
'

test_expect_success 'pull auto merge' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_cloned_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    make_git_commit c c &&
    git pull &&
    assert_git_count 4 &&
    # Merge order appears to be non-deterministic, but I would like to see
    # this better tested.

    cd ..
'

test_expect_success 'pull tags' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_cloned_repo &&
    hg tag tag1 &&
    cd ../git_clone &&
    git pull &&
    git tag | grep tag1 &&

    cd ..
'

test_done