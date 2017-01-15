#!/bin/sh

test_description='Test gitifyhg push tags'

. ./test-lib.sh

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
    test_when_finished "rm -rf hg_repo git_clone .hgrc" &&
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

test_expect_success 'push tag with subsequent commits' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    git tag this_is_a_tag &&
    make_git_commit b test_file &&
    git push origin HEAD --tags &&

    cd ../hg_repo &&
    hg tags | grep this_is_a_tag &&
    assert_hg_messages "Added tag this_is_a_tag for changeset $(hg id --id)${NL}b${NL}a"
    cd ..
'

test_expect_success 'push tag with previous commits' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hgsha1=`hg id --id` &&
    hg tag an_old_tag &&
    clone_repo &&
    make_git_commit b test_file &&
    git tag this_is_a_tag &&
    git push --tags &&

    cd ../hg_repo &&
    hg tags | grep this_is_a_tag &&
    assert_hg_messages "Added tag this_is_a_tag for changeset $(hg id --id -r 2)${NL}b${NL}Added tag an_old_tag for changeset $hgsha1${NL}a" &&

    cd ..
'

test_expect_success 'push messaged tag' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    clone_repo &&
    git tag this_is_a_tag --message="I tagged a message and a user" &&
    git push --tags &&

    cd ../hg_repo &&
    hg tags | grep this_is_a_tag &&
    assert_hg_messages "I tagged a message and a user${NL}a" &&
    hg log &&
    # FIXME: I feel like this should be $GIT_USER
    # but git seems to be passing me the e-mail twice. Is this a bug in
    # git or something gitifyhg needs to parse?
    assert_hg_author "$GIT_AUTHOR_NAME $GIT_AUTHOR_EMAIL <$GIT_AUTHOR_EMAIL>" &&
    cd ..
'

test_expect_success 'push tag different branch' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg branch branch_one &&
    make_hg_commit b test_file &&
    clone_repo &&
    git checkout origin/branches/branch_one --track &&
    git tag this_is_a_tag &&
    git push --tags &&

    cd ../hg_repo &&
    hg tags | grep this_is_a_tag &&
    assert_hg_count 3 &&
    hg update tip &&
    hg branch | grep branch_one &&

    cd ..
'

test_expect_success 'push only new tag' '
    test_when_finished "rm -rf hg_repo git_clone" &&

    make_hg_repo &&
    hg tag an_old_tag &&
    clone_repo &&
    git tag this_is_a_tag &&
    git push --tags &&

    cd ../hg_repo &&
    test `hg tags | wc -l` -eq 3 && # 3 is tip
    hg tags | grep this_is_a_tag &&
    hg tags | grep an_old_tag &&
    assert_hg_count 3 &&

    cd ..
'

test_done
