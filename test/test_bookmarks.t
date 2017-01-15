#!/bin/sh

test_description='Test gitifyhg bookmark management'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

# test_expect_success 'clone bookmark' '
#     test_when_finished "rm -rf hg_repo git_clone" &&
#     make_hg_repo &&
#     hg bookmark featurebookmark &&
#     make_hg_commit b test_file &&

#     clone_repo &&

#     test "`git branch -r`" = "  origin/HEAD -> origin/master
#   origin/featurebookmark
#   origin/master" &&

#     git checkout origin/featurebookmark &&
#     assert_git_messages "b${NL}a" &&
#     git checkout master &&
#     assert_git_messages "b${NL}a" &&

#     cd ..
# '

# test_expect_success 'clone divergent bookmarks' '
#     test_when_finished "rm -rf hg_repo git_clone" &&
#     make_hg_repo &&
#     hg bookmark bookmark_one &&
#     make_hg_commit b test_file &&
#     hg update -r 0 &&
#     make_hg_commit c test_file &&
#     hg bookmark bookmark_two &&
#     make_hg_commit d test_file &&

#     clone_repo &&

#     test "`git branch -r`" = "  origin/HEAD -> origin/master
#   origin/bookmark_one
#   origin/bookmark_two
#   origin/master" &&

#     git checkout origin/bookmark_one &&
#     assert_git_messages "b${NL}a" &&

#     git checkout origin/bookmark_two &&
#     assert_git_messages "d${NL}c${NL}a" &&

#     cd ..
# '

# test_expect_success 'clone bookmark not at tip' '
#     test_when_finished "rm -rf hg_repo git_clone" &&
#     make_hg_repo &&
#     make_hg_commit b test_file &&
#     hg update -r 0 &&
#     hg bookmark bookmark_one &&
#     hg update tip &&

#     clone_repo &&

#     test "`git branch -r`" = "  origin/HEAD -> origin/master
#   origin/bookmark_one
#   origin/master" &&

#     git checkout bookmark_one &&
#     assert_git_messages "a" &&
#     git checkout master &&
#     assert_git_messages "b${NL}a" &&

#     cd ..
# '

# # See issue #13
# test_expect_success 'clone bookmark named master not at tip' '
#     test_when_finished "rm -rf hg_repo git_clone" &&
#     make_hg_repo &&
#     make_hg_commit b test_file &&
#     hg update -r 0 &&
#     hg bookmark master &&
#     hg update tip &&

#     clone_repo &&

#     cd ..
# '

test_expect_success 'push to bookmark' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg bookmark feature &&
    make_hg_commit b test_file &&
    clone_repo &&
    git checkout --track origin/feature &&
    make_git_commit c test_file &&
    git push &&

    cd ../hg_repo &&
    hg update &&

    assert_hg_messages "c${NL}b${NL}a" &&
    hg bookmark | grep feature &&
    hg update feature &&
    test_cmp test_file ../git_clone/test_file &&

    cd ..
'

# test_expect_success 'push multiple bookmarks' '
#     test_when_finished "rm -rf hg_repo git_clone" &&

#     make_hg_repo &&
#     hg bookmark feature &&
#     make_hg_commit b test_file &&
#     hg update --rev 0 &&
#     hg bookmark feature2 &&
#     make_hg_commit c test_file &&

#     clone_repo &&
#     git checkout --track origin/feature &&
#     make_git_commit d test_file &&
#     git push &&

#     cd ../hg_repo &&
#     assert_hg_messages "d${NL}c${NL}b${NL}a" &&
#     assert_hg_messages "a${NL}b${NL}d" "0..feature" &&
#     assert_hg_messages "a${NL}c" "0..feature2" &&

#     hg update feature &&
#     hg bookmark | grep feature &&
#     test_cmp test_file ../git_clone/test_file &&

#     cd ..
# '

# test_expect_success 'push new bookmark' '
#     test_when_finished "rm -rf hg_repo git_clone" &&

#     make_hg_repo &&
#     clone_repo &&
#     git checkout -b anewbranch &&
#     make_git_commit b test_file &&
#     git push --set-upstream origin anewbranch &&

#     cd ../hg_repo &&
#     assert_hg_messages "b${NL}a" &&
#     hg bookmark | grep anewbranch &&
#     hg tip | grep anewbranch &&

#     cd ..
# '

# test_expect_failure 'pull_from_bookmark' '
#     test_when_finished "rm -rf hg_repo git_clone" &&

#     make_hg_repo &&
#     hg bookmark feature &&
#     make_hg_commit b test_file &&
#     hg update -r 0 &&
#     hg bookmark feature2 &&
#     make_hg_commit c test_file &&

#     clone_repo &&
#     git checkout origin/feature --track &&
#     assert_git_messages "b${NL}a" &&

#     cd ../hg_repo &&
#     hg update feature &&
#     make_hg_commit d test_file &&
#     hg update feature2 &&
#     make_hg_commit e test_file &&

#     cd ../git_clone &&
#     git pull origin feature &&
#     assert_git_messages "d${NL}b${NL}a" &&
#     git checkout origin/feature2 --track &&
#     assert_git_messages "c${NL}a" &&

#     git pull origin feature2 &&
#     assert_git_messages "e${NL}c${NL}a" &&

#     # TODO: Pulling into a bookmark does not seem to be working. Find the
#     # problem and fix.

#     cd ..
# '

test_done
