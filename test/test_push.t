#!/bin/sh

test_description='Test gitifyhg push'

. ./test-lib.sh

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
    assert_hg_messages "c${NL}b${NL}a" &&
    hg update tip &&
    test `hg branch` = "branch_one" &&

    cd ..
'

test_expect_success 'push merged named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch branch-one &&
    make_hg_commit b1 b &&
    hg update default &&
    make_hg_commit c1 c &&

    clone_repo &&
    git merge origin/branches/branch_one &&
    git push &&

    cd ../hg_repo &&
    hg update &&
    hg log --template="{desc}" &&
    assert_hg_messages "Merge${NL}c1${NL}b1${NL}a"

    cd ..
'

test_expect_success 'push new named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    git checkout -b branches/branch_one &&
    make_git_commit b test_file &&
    git push --set-upstream origin branches/branch_one &&

    cd ../hg_repo &&
    assert_hg_messages "b${NL}a"
    hg update tip &&
    test `hg branch` = "branch_one" &&

    cd ..
'

test_expect_success 'push conflict named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch feature &&
    make_hg_commit b test_file &&
    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit c test_file &&
    cd ../git_clone &&
    git checkout --track origin/branches/feature &&
    make_git_commit d test_file &&
    test_expect_code 1 git push &&

    cd ..
'

test_expect_success 'fetch after bad push updates master' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    make_git_commit c c &&
    test_expect_code 1 git push &&
    git fetch &&
    assert_git_messages "b${NL}a" origin/master &&
    git pull --rebase &&
    assert_git_messages "c${NL}${NL}b${NL}a" &&
    git push &&
    cd ../hg_repo &&
    hg log --template="{desc}\n"
    assert_hg_messages "c${NL}b${NL}a" &&

    cd ..
'
test_expect_success 'test push after merge' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit b "test_file" &&
    cd ../git_clone &&
    make_git_commit c c &&
    git pull && # automatically merges 
    assert_git_count 4 &&
    git push &&
    cd ../hg_repo &&
    assert_hg_count 4 &&

    cd ..
'

test_expect_success 'push two commits' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    make_git_commit c test_file &&
    git push &&
    cd ../hg_repo &&
    assert_hg_messages "c${NL}b${NL}a"
    cd ..
'

test_expect_success 'push up to date' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    git push 2>&1 | grep "Everything up-to-date" &&

    # push with a commit on hg default/git master
    cd ../hg_repo &&
    make_hg_commit b test_file &&
    cd ../git_clone &&
    git pull &&
    git push 2>&1 | grep "Everything up-to-date" &&

    # push with a commit on non-default branch
    cd ../hg_repo &&
    hg branch new_branch &&
    make_hg_commit c test_file &&
    cd ../git_clone &&
    git pull &&
    git checkout origin/branches/new_branch --track &&
    git push 2>&1 | grep "Everything up-to-date" &&

    make_git_commit d test_file &&
    out=`git push origin branches/new_branch 2>&1` &&
    echo -e $out &&
    echo $out | grep "branches/new_branch -> branches/new_branch" &&

    cd ..
'

test_expect_success 'test git push messages' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    out=`git push 2>&1` &&
    ! echo $out | grep "new branch" &&
    echo $out | grep "master -> master" &&

    git checkout -b branches/test_branch &&
    make_git_commit c test_file &&
    out=`git push --set-upstream origin branches/test_branch 2>&1` &&
    echo $out | grep "new branch" &&
    echo $out | grep "branches/test_branch -> branches/test_branch" &&

    make_git_commit c test_file &&
    out=`git push 2>&1` &&
    ! echo $out | grep "new branch" &&
    echo $out | grep "branches/test_branch -> branches/test_branch" &&

    cd ..
'


test_expect_success 'handle paths with whitespace' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    clone_repo &&
    make_git_commit b "test file" &&
    git push &&
    # Make sure that the remote ref has updated
    test "`git log --pretty=format:%B origin`" = "b${NL}${NL}a" &&

    cd ../hg_repo &&
    assert_hg_messages "b${NL}a" &&
    hg update &&
    test_cmp "../git_clone/test file" "test file" &&

    cd ..
'


test_done
