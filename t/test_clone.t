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

test_expect_success 'basic clone with default branch and two commits' '
    make_hg_repo &&
    cd hg_repo &&
    make_hg_commit b test_file &&
    cd .. &&
    clone_repo &&
    test_expect_code 0 ls | grep git_clone &&
    test_cmp hg_repo/test_file git_clone/test_file &&
    test -d git_clone/.git &&
    cd git_clone &&
    assert_git_messages "b${NL}a"
'
test_expect_success 'clone linear branch, no multiple parents' '
    make_hg_repo &&
    cd hg_repo &&
    hg branch featurebranch &&
    make_hg_commit b test_file &&
    cd .. &&
    clone_repo &&
    test_expect_code 0 ls | grep git_clone &&
    cd git_clone &&
    assert_git_messages "a" &&
    git branch -r &&
    test "`git branch -r`" = "    origin/HEAD -> origin/master
    origin/branches/featurebranch
    origin/master"
'
test_expect_success ' clone simple divergent branch' '
    make_hg_repo
'

