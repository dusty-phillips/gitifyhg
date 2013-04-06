#!/bin/sh
#
# Copyright (c) 2012 Felipe Contreras
#
# Base commands from hg-git tests:
# https://bitbucket.org/durin42/hg-git/src
#

test_description='Test remote-hg'

. ./test-lib.sh

# if ! test_have_prereq PYTHON; then
# 	skip_all='skipping remote-hg tests; python not available'
# 	test_done
# fi

# if ! "$PYTHON_PATH" -c 'import mercurial'; then
# 	skip_all='skipping remote-hg tests; mercurial not available'
# 	test_done
# fi

check () {
	(cd $1 &&
	git log --format='%s' -1 &&
	git symbolic-ref HEAD) > actual &&
	(echo $2 &&
	echo "refs/heads/$3") > expected &&
	test_cmp expected actual
}

setup () {
	(
	echo "[ui]"
	echo "username = H G Wells <wells@example.com>"
	) >> "$HOME"/.hgrc
}

setup

test_expect_success 'cloning' '
  test_when_finished "rm -rf gitrepo*" &&

  (
  hg init hgrepo &&
  cd hgrepo &&
  echo zero > content &&
  hg add content &&
  hg commit -m zero
  ) &&

  git clone "gitifyhg::$PWD/hgrepo" gitrepo &&
  check gitrepo zero master
'


# Note: In the following test, remote-hg checks for "next next" here
# in the first "check". That is, it checks that the active branch
# in the git clone matches the active branch in the hg remote.
# This agrees with the git semantics for cloning.
# But we (for now?) intentionally follow the hg semantics instead,
# which sets the working tree to the default branch instead.
test_expect_success 'cloning with branches' '
  test_when_finished "rm -rf gitrepo*" &&

  (
  cd hgrepo &&
  hg branch next &&
  echo next > content &&
  hg commit -m next
  ) &&

  git clone "gitifyhg::$PWD/hgrepo" gitrepo &&
  check gitrepo zero master &&

  (cd hgrepo && hg checkout default) &&

  git clone "gitifyhg::$PWD/hgrepo" gitrepo2 &&
  check gitrepo2 zero master
'

# See above: In the following test, remote-hg checks for
# "feature-a feature-a", but we instead check for "feature-a master"
# which matches hg (but not git) semantics.
test_expect_success 'cloning with bookmarks' '
  test_when_finished "rm -rf gitrepo*" &&

  (
  cd hgrepo &&
  hg bookmark feature-a &&
  echo feature-a > content &&
  hg commit -m feature-a
  ) &&

  git clone "gitifyhg::$PWD/hgrepo" gitrepo &&
  check gitrepo feature-a master
'

# Again, see above comments for why this test differs from remote-hg.
test_expect_success 'cloning with detached head' '
  test_when_finished "rm -rf gitrepo*" &&

  (
  cd hgrepo &&
  hg update -r 0
  ) &&

  git clone "gitifyhg::$PWD/hgrepo" gitrepo &&
  check gitrepo feature-a master
'

test_expect_success 'update bookmark' '
  test_when_finished "rm -rf gitrepo*" &&

  (
  cd hgrepo &&
  hg bookmark devel
  ) &&

  (
  git clone "gitifyhg::$PWD/hgrepo" gitrepo &&
  cd gitrepo &&
  git checkout devel &&
  echo devel > content &&
  git commit -a -m devel &&
  git push
  ) &&

  hg -R hgrepo bookmarks | grep "devel\s\+3:"
'

test_done
