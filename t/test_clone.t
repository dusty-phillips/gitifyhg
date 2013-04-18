#!/bin/sh

test_description='Test gitifyhg clones'

source ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#   skip_all='skipping gitifyhg tests; python not available'
#   test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#   skip_all='skipping gitifyhg tests; mercurial not available'
#   test_done
# fi

test_expect_success 'basic clone with default branch and two commits' '
  make_hg_repo &&
  cd hg_repo &&
  make_hg_commit b test_file &&
  cd .. &&
  test_expect_code 0 git clone gitifyhg::hg_repo git_clone &&
  test_expect_code 0 ls | grep git_clone &&
  test_cmp hg_repo/test_file git_clone/test_file &&
  test -d git_clone/.git &&
  cd git_clone &&
  test "`git log --pretty=format:%B`" = "b${NL}a"
'

test_done