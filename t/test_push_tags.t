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

test_expect_success 'push lightweight tag' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    git tag "this_is_a_tag" &&
    git push --tags &&

    cd ../hg_repo &&
    hg tags | grep "this_is_a_tag" &&
    assert_hg_count 2 &&

    cd ..
'

# FIXME: See #77
test_expect_success 'lightweight tag sets hg username' '
    test_when_finished "rm -rf hg_repo git_clone" &&
    user="Lite Wait <litewait@example.com>" &&

    # NOTE: sharness set #HOME to the working directory for us, so this is
    # the default hgrc.
    echo "[ui]${NL}username=$user" > .hgrc 
    make_hg_repo &&
    clone_repo &&
    git tag "lightweight" &&
    git push --tags &&

    cd ../hg_repo &&
    assert_hg_count 2 &&
    assert_hg_author "$user" &&

    cd ..
'



test_done