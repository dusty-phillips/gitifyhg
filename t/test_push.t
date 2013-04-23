#!/bin/sh

test_description='Test gitifyhg push'

source ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'simple push from master' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    # Make sure that the remote ref has updated
    test "`git log --pretty=format:%B origin`" = "b${NL}${NL}a" &&

    cd ../hg_repo &&
    assert_hg_messages "b${NL}a" &&
    hg update &&
    test_cmp ../git_clone/test_file test_file &&

    cd ..
'

test_expect_failure 'push not create bookmark' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    cd ../hg_repo &&

    test `hg bookmarks` = "no bookmarks set" &&

    cd ..
'

test_expect_success 'test push empty repo' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    mkdir hg_repo &&
    cd hg_repo &&
    hg init &&
    
    clone_repo &&
    git status | grep "Initial commit" &&
    make_git_commit a test_file &&
    git push origin master &&
    cd ../hg_repo &&
    assert_hg_messages "a" &&
    hg update &&
    test_cmp test_file ../git_clone/test_file &&

    cd ..
'

test_expect_success 'push conflict default' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&

    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    make_git_commit c test_file &&
    test_expect_code 1 git push &&
    # test it again because we were having issues with it succeeding the second time
    test_expect_code 1 git push &&

    cd ..
'

test_expect_success 'push to named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch branch_one &&
    make_hg_commit b test_file &&

    clone_repo &&
    git checkout -t "origin/branches/branch_one" &&
    make_git_commit c test_file &&
    git push &&

    cd ../hg_repo &&
    hg log --template="{desc}\n" &&
    assert_hg_messages "c${NL}b${NL}a" &&
    hg update tip &&
    test `hg branch` == "branch_one" &&

    cd ..
'

test_done
