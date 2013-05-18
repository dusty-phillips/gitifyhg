#!/bin/sh

test_description='Test gitifyhg authors'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
#    skip_all='skipping gitifyhg tests; python not available'
#    test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
#    skip_all='skipping gitifyhg tests; mercurial not available'
#    test_done
# fi

test_expect_success 'push email is correct' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    make_git_commit b test_file &&
    git push &&
    cd ../hg_repo &&
    hg update &&
    assert_hg_author "$GIT_USER" &&
    make_hg_commit "c" test_file &&
    assert_hg_author "$HG_USER" &&
    cd ../git_clone &&
    git pull &&
    assert_git_author "$GIT_USER" "HEAD^" &&
    assert_git_author "$HG_USER" &&


    cd ..
'

test_expect_success 'author all good' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "all is good <all.good@example.com>" &&

    clone_repo &&
    git show -s --format="%an <%ae>"
    assert_git_author "all is good <all.good@example.com>" &&

    cd ..
'

test_expect_success 'author no email' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "no email supplied" &&

    clone_repo &&
    assert_git_author "no email supplied <>" &&

    cd ..
'

test_expect_success 'author only email' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "<email@example.com>" &&

    clone_repo &&
    assert_git_author "Unknown <email@example.com>" &&

    cd ..
'

test_expect_success 'author not quoted only email' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "email@example.com" &&

    clone_repo &&
    assert_git_author "Unknown <email@example.com>" &&

    cd ..
'

test_expect_success 'author no spaces before email' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "no space before email<email@example.com>" &&

    clone_repo &&
    assert_git_author "no space before email <email@example.com>" &&

    cd ..
'

# See #22
test_expect_success 'author no email quoting' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "no email quoting email@example.com" &&

    clone_repo &&
    assert_git_author "no email quoting <email@example.com>" &&

    cd ..
'

# See #22
test_expect_success 'author missing end quote' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "missing end quote <email@example.com" &&

    clone_repo &&
    assert_git_author "missing end quote <email@example.com>" &&

    cd ..
'

test_expect_success 'author obfuscated email' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "Author <obfuscated (at) email dot address>" &&

    clone_repo &&
    assert_git_author "Author <obfuscated (at) email dot address>" &&

    cd ..
'

test_expect_success 'author abuse quotes' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    make_hg_commit b test_file "totally >>> bad <<< quote can be used in hg <><><" &&

    clone_repo &&
    assert_git_author "totally <bad  quote can be used in hg>" &&

    cd ..
'


test_done
