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
    ls &&
    echo "AAAA"
    cd .. &&
    ls &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&

    cd ../hg_repo &&
    assert_hg_messages "b${NL}a" **
    hg update &&
    test_cmp ../git_clone/test_file test_file &&

    cd ..
'


test_done
