#!/bin/sh

test_description='Test various file operations in gitifyhg clones'

source ./test-lib.sh

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

    cd .. &&
    echo "a"
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

    cd .. &&
    clone_repo &&
    test -d dir_or_file &&
    test -f dir_or_file/test_file &&

    cd ..
'

test_expect_success 'clone replace directory with a file' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    mkdir dir_or_file &&
    make_hg_commit "b" dir_or_file/test_file &&
    hg rm dir_or_file/test_file &&
    make_hg_commit "c" dir_or_file &&

    cd .. &&
    clone_repo &&

    test -f dir_or_file &&

    cd ..
'

test_done
