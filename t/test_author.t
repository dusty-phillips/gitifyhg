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

test_expect_success 'push email is correct' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    cd ../hg_repo &&
    hg update &&
    assert_hg_author "$GIT_USER" &&
    make_hg_commit "c" test_file &&
    assert_hg_author "$HG_USER" &&
    cd ../git_clone &&
    git pull &&
    assert_git_author "$GIT_USER" "HEAD^" &&
    assert_git_author "$HG_USER" &&


    cd ..
'

test_done