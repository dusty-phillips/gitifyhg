#!/bin/sh

test_description='Test gitifyhg clone, pull, and push with spaces'

source ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_failure 'anonymous branches dont work' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file &&
    hg update -r 0 &&
    make_hg_commit c test_file &&
    cd .. &&

    git clone testgitifyhg::hg_repo git_clone 2>&1 | grep "more than one head" &&

    # TODO: "more than one head" is the correct response for now, but a more
    # appropriate result would be to clone the extra commits, perhaps naming
    # the branch anonymous/<sha> or something. assert False to mark an expected
    # failure. 
    
    false &&

    cd ..
'

test_expect_failure 'anonymous branch from named branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    hg branch featurebranch &&
    make_hg_commit b test_file &&
    make_hg_commit c test_file &&
    hg update -r 1 &&
    make_hg_commit d test_file &&
    hg update default &&
    make_hg_commit e test_file &&

    cd .. &&
    git clone testgitifyhg::hg_repo git_clone 2>&1 | grep "more than one head" &&
    cd git_clone &&
    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/branches/featurebranch
  origin/master" &&

    # TODO: Same issue as above test.

    false &&

  cd ..
'

test_expect_failure 'pull from anonymous branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file &&

    clone_repo &&
    cd ../hg_repo &&
    make_hg_commit c test_file &&
    hg update --rev=-2 &&
    make_hg_commit c2 test_file &&

    cd ../git_clone &&
    git pull &&

    # TODO: pulling anonymous branches are currently pruned, need to test
    # and assert that they are actually dealt with properly.
    false &&

    cd ..
'

test_done