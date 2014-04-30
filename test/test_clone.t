#!/bin/sh

test_description='Test gitifyhg clones'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'basic clone with default branch and two commits' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    make_hg_commit b test_file &&
    clone_repo &&
    test_cmp ../hg_repo/test_file test_file &&
    test -d .git &&
    assert_git_messages "b${NL}a" &&

    cd ..
'
test_expect_success 'clone linear branch, no multiple parents' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    hg branch featurebranch &&
    make_hg_commit b test_file &&
    clone_repo &&
    assert_git_messages "a" &&
    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/branches/featurebranch
  origin/master" &&

    git checkout branches/featurebranch &&
    test_cmp ../hg_repo/test_file test_file &&
    assert_git_messages "b${NL}a" &&

    cd ..
'

test_expect_success 'clone simple divergent branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    make_hg_repo &&
    hg branch featurebranch &&
    make_hg_commit b test_file &&
    hg update default &&
    make_hg_commit c c &&
    clone_repo &&
    assert_git_messages "c${NL}a" &&
    git checkout "origin/branches/featurebranch" &&
    assert_git_messages "b${NL}a" &&

    cd ..
'

test_expect_success 'clone merged branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch featurebranch &&
    make_hg_commit b test_file &&
    hg update default &&
    make_hg_commit c c &&
    hg merge featurebranch &&
    hg commit -m "merge" &&
    make_hg_commit d test_file &&

 clone_repo &&

    assert_git_messages "d${NL}merge${NL}c${NL}b${NL}a" &&
    git checkout origin/branches/featurebranch &&
    assert_git_messages "b${NL}a"

    cd ..
'

test_expect_success 'clone basic tag' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file &&
    hg tag "this_is_tagged" &&
    make_hg_commit c test_file &&

    clone_repo &&

    test $(git tag) = "this_is_tagged" &&
    git checkout this_is_tagged &&
    assert_git_messages "b${NL}a" &&

    cd ..
'

test_expect_success 'clone close branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    test_when_finished "unset GITIFYHG_ALLOW_CLOSED_BRANCHES" &&

    export GITIFYHG_ALLOW_CLOSED_BRANCHES=on &&
    make_hg_repo &&
    hg branch feature &&
    make_hg_commit b b &&
    hg update default &&
    make_hg_commit c c &&
    hg update feature &&
    echo d >> b &&
    hg commit --close-branch -m "d" &&

    clone_repo &&
    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/branches/feature
  origin/master" &&
    assert_git_messages "c${NL}a" &&
    git checkout origin/branches/feature &&
    assert_git_messages "d${NL}b${NL}a" &&

    cd ..
'

test_expect_success 'no implicit clone close branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    echo $GITIFYHG_ALLOW_CLOSED_BRANCHES &&

    make_hg_repo &&
    hg branch feature &&
    make_hg_commit b b &&
    hg update default &&
    make_hg_commit c c &&
    hg update feature &&
    echo d >> b &&
    hg commit --close-branch -m "d" &&

    clone_repo &&
    git branch -r &&
    test "`git branch -r`" = "  origin/HEAD -> origin/master
  origin/master" &&
    assert_git_messages "c${NL}a" &&

    cd ..
'

test_expect_success 'ensure commit message match' '
    test_when_finished "rm -rf repo_a repo_b repo_c" &&

    (
    hg init repo_a &&
    cd repo_a &&
    echo "a" >> test_file &&
    hg add test_file &&
    hg commit --message="a" &&
    echo "b" >> test_file &&
    hg commit --message="b"
    ) &&

    (
    git init repo_b &&
    cd repo_b &&
    echo "a" >> test_file &&
    git add test_file &&
    git commit -a --message="a" &&
    echo "b" >> test_file &&
    git commit -a --message="b"
    ) &&

    git clone "gitifyhg::repo_a" repo_c &&

    printf "%s\n\0" "b" "a" > expected &&
    git --git-dir=repo_b/.git log -z --format="%B" > actual &&
    test_cmp expected actual &&
    git --git-dir=repo_c/.git log -z --format="%B" > actual &&
    test_cmp expected actual &&
    hg -R repo_a log --template="{desc}\n\0" > actual &&
    test_cmp expected actual
'

test_done
