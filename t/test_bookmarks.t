#!/bin/sh

test_description='Test gitifyhg clones'

source ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'clone bookmark' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    hg bookmark featurebookmark &&
    make_hg_commit b test_file &&

    clone_repo &&

    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/featurebookmark
  origin/master" &&

    git checkout origin/featurebookmark &&
    assert_git_messages "b${NL}a" &&
    git checkout master &&
    assert_git_messages "b${NL}a" &&

    cd ..
'

test_expect_success 'clone divergent bookmarks' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    hg bookmark bookmark_one &&
    make_hg_commit b test_file &&
    hg update -r 0 &&
    make_hg_commit c test_file &&
    hg bookmark bookmark_two &&
    make_hg_commit d test_file &&

    clone_repo &&

    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/bookmark_two
  origin/master" &&

    git checkout origin/bookmark_one &&
    assert_git_messages "b${NL}a" &&

    git checkout origin/bookmark_two &&
    assert_git_messages "d${NL}c${NL}a" &&

    cd ..
'

test_expect_success 'clone bookmark not at tip' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    make_hg_commit b test_file &&
    hg update -r 0 &&
    hg bookmark bookmark_one &&
    hg update tip &&

    clone_repo &&

    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/bookmark_one
  origin/master" &&

    git checkout bookmark_one &&
    assert_git_messages "a" &&
    git checkout master &&
    assert_git_messages "b${NL}a" &&

    cd ..
'

# See issue #13
test_expect_success 'clone bookmark named master not at tip' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    make_hg_commit b test_file &&
    hg update -r 0 &&
    hg bookmark master &&
    hg update tip &&

    clone_repo &&

    cd ..
'

test_done