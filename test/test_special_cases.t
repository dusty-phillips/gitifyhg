#!/bin/sh

test_description='Test gitifyhg notes'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

SB=$'\xE2\x98\xA0'

test_expect_success 'unicode paths' '
    # NOTE: This is failing, but I do not know why. It works in py.test.
    # The error is in os.getcwdu. I am not sure if it is a test problem or
    # a bug in gitifyhg.

    # This test has been ported from py.test but not fully tested due to the
    # early error.
    oldlang=$LANG &&
    oldlc=$LC_ALL &&
    export LANG="en_US.utf8" &&
    export LC_ALL="en_US.utf8" &&
    test_when_finished "rm -rf hg${SB}repo git${SB}clone" &&
    test_when_finished "export LANG=$oldlang" &&
    test_when_finished "export LC_ALL=$oldlc" &&

    mkdir hg${SB}repo &&
    cd hg${SB}repo &&
    echo $SB > file${SB} &&
    hg init &&
    hg add file${SB} &&
    hg commit -m ${SB} --user="$HG_USER" &&
    cd .. &&
    git clone gitifyhg::hg${SB}repo git${SB}clone &&
    cd git${SB}clone &&
    git config user.email $GIT_AUTHOR_EMAIL &&
    git config user.name "$GIT_USER"
    assert_git_messages "${SB}" &&

    echo ${SB} >> file${SB} &&
    git add file${SB} &&
    git commit -m ${SB}2 &&
    git push &&
    cd ../hg${SB}repo &&
    hg update &&
    assert_hg_messages "${SB}2${NL}${SB}" &&

    echo ${SB} >> file${SB} &&
    hg commit -m "${SB}3" --user="$HG_USER" &&

    cd ../git${SB}clone &&
    git pull &&
    assert_git_messages "${SB}3${NL}${SB}2${NL}${NL}${SB}" &&

    cd ..
'

test_expect_success 'executable bit' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    echo b >> test_file &&
    chmod 644 test_file &&
    hg commit -m "make file" &&
    chmod 755 test_file &&
    hg commit -m "make executable" &&
    chmod 644 test_file &&
    hg commit -m "make unexecutable" &&

    clone_repo &&
    test ! -x test_file &&
    git checkout HEAD^ &&
    test -x test_file &&
    git checkout HEAD^ &&
    test ! -x test_file &&

    git checkout master &&
    chmod 755 test_file &&
    git add test_file &&
    git commit -m "make executable again" &&
    git push &&

    cd ../hg_repo &&
    hg update &&
    test -x test_file &&

    cd ..
'
test_expect_success 'symlinks' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    ln -s test_file linked &&
    hg add linked &&
    hg commit -m c &&

    clone_repo &&
    test -L linked &&
    ln -s test_file second_link &&
    git add second_link &&
    git commit -m d &&
    git push &&

    cd ../hg_repo &&
    hg update &&
    test -L second_link &&

    cd ..
'

test_done


here
