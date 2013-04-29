#!/bin/sh

test_description='Test various file operations in gitifyhg clones'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'cloning a removed file works' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file &&
    echo "b"
    hg rm test_file &&
    hg commit -m "c" &&

    clone_repo &&
    
    test_expect_code 2 ls test_file &&

    cd ..
'

# See issue #36
test_expect_failure 'cloning a file replaced with a directory' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit "b" dir_or_file &&

    hg rm dir_or_file &&
    mkdir dir_or_file &&
    make_hg_commit c dir_or_file/test_file &&

    clone_repo &&
    test -d dir_or_file &&
    test -f dir_or_file/test_file &&

    cd ..
'

# also issue #36
test_expect_failure 'clone replacing a symlink with a directory' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    ln -s test_file dir_or_link &&
    hg add dir_or_link &&
    hg commit -m "b" &&
    hg rm dir_or_link &&
    mkdir dir_or_link &&
    make_hg_commit c dir_or_link/test_file &&

    clone_repo &&

    test -d dir_or_link &&
    test -f dir_or_link/test_file &&

    cd ..
'

test_expect_success 'clone replace directory with a file' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    mkdir dir_or_file &&
    make_hg_commit "b" dir_or_file/test_file &&
    hg rm dir_or_file/test_file &&
    make_hg_commit "c" dir_or_file &&

    clone_repo &&

    test -f dir_or_file &&

    cd ..
'

test_expect_success 'clone replace file with a symlink' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b link_or_file &&
    hg rm link_or_file &&
    ln -s test_file link_or_file &&
    hg add link_or_file &&
    hg commit -m "c" &&

    clone_repo &&

    test -f link_or_file &&
    test -L link_or_file &&

    cd ..
'

test_expect_success 'clone replace directory with symlink' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    mkdir dir_or_link &&
    make_hg_commit b dir_or_link/test_file &&
    hg rm dir_or_link/test_file &&
    ln -s test_file dir_or_link &&
    hg add dir_or_link &&
    hg commit -m c

    clone_repo &&

    test -f dir_or_link &&
    test -L dir_or_link &&

    cd ..
'

test_done
