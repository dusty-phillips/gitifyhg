from path import path as p
import sh


# HELPERS
# =======
def write_to_test_file(message, filename='test_file'):
    '''Append the message to the 'test_file' file in the current working
    directory or filename if it was passed. This is normally done to stage a
    commit in hg or git.

    :param message: Something to be appended to the test file. Use \\n
        judiciously.
    :param filename: A filename to commit to. If unsupplied, test_file
        will be updated.'''
    with p(filename).open('a') as file:
        file.write(message)


def make_hg_commit(message, filename='test_file'):
    '''Assuming we are in a mercurial repository, write the message to the
    filename and commit it.'''
    add = not p(filename).exists()
    write_to_test_file(message, filename)
    if add:
        sh.hg.add(filename)
    sh.hg.commit(message=message)


def make_git_commit(message, filename='test_file'):
    '''Assuming we are in a git repository, write the message to the
    filename and commit it.'''
    write_to_test_file(message, filename)
    sh.git.add(filename)
    sh.git.commit(message=message)


def clone_repo(git_dir, hg_repo):
    '''Simple helper for the common task of cloning the given mercurial
    repository into the git directory. Changes the current working directory
    into the repository and returns the full path to the repository.'''
    sh.cd(git_dir)
    sh.git.clone("gitifyhg::" + hg_repo)
    git_repo = git_dir.joinpath('hg_base')
    sh.cd(git_repo)
    return git_repo


def assert_git_count(count):
    '''Assuming you are in a git repository, assert that ``count`` commits
    have been made to that repo.'''
    assert sh.git.log(pretty='oneline').stdout.count(b'\n') == count


def assert_git_messages(expected_lines):
    '''Assert that logging all git messages in order provides the given lines
    of output.

    :param expected_lines: The a list of str messages  that were passed into
        git or hg when commited, in reverser order
        (ie: most recent commits at the top or left)
    :return True if the message lines match the git repo in the current directory
        False otherwise.'''
    actual_lines = sh.git('--no-pager', 'log', pretty='oneline', color='never'
        ).strip().split('\n')
    actual_lines = [l.partition(' ')[-1] for l in actual_lines]
    assert actual_lines == expected_lines


def assert_hg_count(count, rev=None):
    '''Assuming you are in an hg repository, assert that ``count`` commits
    have been made to that repo.'''
    if rev:
        assert sh.grep(sh.hg.log(rev=rev), 'changeset:').stdout.count(b'\n') == count
    else:
        assert sh.grep(sh.hg.log(), 'changeset:').stdout.count(b'\n') == count
