#!/bin/sh

test_description='Test gitifyhg notes'

source ./test-lib.sh

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
    export LANG='en_US.utf8' &&
    test_when_finished "rm -rf hg${SB}repo git${SB}clone" &&
    test_when_finished "export LANG=$oldlang" &&

    mkdir hg${SB}repo &&
    cd hg${SB}repo &&
    echo $SB > file${SB} &&
    hg init &&
    hg add file${SB} &&
    hg commit -m ${SB} &&
    cd ..
    git clone testgitifyhg::hg${SB}repo git${SB}clone &&
    cd git${SB}clone &&
    assert_git_messages "${SB}" &&

    echo ${SB} >> file${SB} &&
    git add file${SB} &&
    git commit -m ${SB}2 &&
    cd ../hg${SB}repo &&
    assert_hg_messages "${SB}2${NL}${SB}" &&

    echo ${SB} >> file${SB} &&
    hg commit -m "${SB}3" &&

    cd ../git${SB}clone &&
    git pull &&
    assert_git_messages "${SB}3${NL}${SB}2${NL}${SB}" &&


    cd ..
'

test_done


here