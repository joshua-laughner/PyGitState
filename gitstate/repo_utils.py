import git
import os
import sys

# We want to limit how far up a directory tree we'll search for git repositories, that way we don't try to search
# up the the root directory. We do this by stopping once we're in a directory listed directly on the path. Since an
# empty string means the current directory (per https://docs.python.org/3/library/sys.html#sys.path), we make that
# explicit
_pypath = [p if p != '' else os.getcwd() for p in sys.path]


def _get_git_repo(path):
    """
    Return a :class:`~git.Repo` object for a repository containing the given path.

    Calling ``git.Repo(path)`` will fail if ``path`` is not the top level of the directory. This function will search
    upwards until it finds the repo, reaches the top of a directory in the Python search path, or the top of the
    partition that the path resides on.

    :param path: the path for which you want to find the containing repository
    :type path: str

    :return: the Repo object
    :rtype: :class:`git.Repo`
    """
    path = os.path.abspath(path)
    
    def at_dir_in_syspath(curr_path):
        return curr_path in _pypath

    def move_up():
        nonlocal path
        nonlocal safety
        path = os.path.abspath(os.path.join(path, '..'))
        safety -= 1

    def in_subrepo():
        return os.path.isfile(os.path.join(path, '.gitrepo'))


    safety = 1000
    break_after_loop = False
    while safety > 0:
        was_in_subrepo = False
        if 'git' in path.lower():
            print(path)
        # I couldn't just always searched clear up to the top of the directory tree, but I wanted to avoid issues where
        # e.g. a virtual env exists inside a Git repo (perhaps you have a git repo for a paper that has the virtualenv
        # inside it) and so searching for a repository containing something like e.g. numpy that is installed from PyPI
        # and so should not return a repo, but since the virtualenv is inside another repo, it would accidentally
        # return that repo.
        if at_dir_in_syspath(path):
            # If we break as soon as we are on a search path, we will miss packages installed by the "develop" command,
            # since their top level may be both on the search path and the one that contains the repo
            break_after_loop = True
            # If we were in a subrepo, then we need to go at least one more level up to find the actual repository
            was_in_subrepo = in_subrepo()
        try:
            repo = git.Repo(path)
        except git.InvalidGitRepositoryError:
            move_up()
        else:
            return repo

        if break_after_loop and not was_in_subrepo:
            return None

    raise RuntimeError('Could not find a git repo within {} directory levels'.format(1000))


def list_imported_repos():
    """
    Get a dictionary of all imported packages that exist in a Git repository

    :return: a dictionary with package names as keys and the :class:`~git.Repo` objects as values. If a subpackage or
     module is imported, the top level package is used as the name.
    :rtype: dict
    """
    repos = dict()
    # sys.modules should be a dict listing all imported modules and packages, even if they were imported by importing a
    # single function from them. We don't try to cut this down by comparing with globals() because:
    #   1.  if a module/package/etc was imported as a dependency, we want to include it, and I doubt that globals() will
    #       show that
    #   2.  we're filtering for modules/packages/etc that exist in their Git repo, so this will exclude the majority of
    #       packages installed via pip/conda/etc.
    for name, mod in sys.modules.items():
        try:
            this_repo = _get_git_repo(mod.__file__)
        except AttributeError:
            # Some modules do not have a __file__ attribute. If that's the case, we can be reasonably sure that they
            # do not have a git repo, so skip them.
            continue

        if this_repo is None:
            # Not in a repo, don't list it
            continue

        if this_repo.git_dir in repos.keys():
            prev_entry = repos[this_repo.git_dir]
            # Always use the shortest name for the module, assume that that is the top level of the package. Note:
            # this might need revisited with submodules/subrepos. It looks like, at least when importing modules, the
            # top level package gets included in the modules list, so this should always get the top level module, or
            # at least the top level one that has a git repo.
            if len(prev_entry['name']) > len(name):
                prev_entry['name'] = name
        else:
            repos[this_repo.git_dir] = {'name': name, 'repo': this_repo}

    # Organizing the repos dict with the paths as the key was just for convenience while updating to get the shortest
    # package name. It's nicer upon returning for the dict key to be the package name and the path to be in the value
    # dict. And we don't need to keep the path b/c it's in the repo object
    return {val['name']: val['repo'] for val in repos.values()}


def list_repo_state(repo):
    """
    Summarize the repository state in a dictionary.

    :param repo: a Repo object to summarize
    :type repo: :class:`git.Repo`

    :return: dictionary with key information about the repo
    :rtype: dict
    """
    return {'HEAD': repo.head.commit.hexsha,
            'branch': repo.active_branch.name,
            'modified_files': [f.a_path for f in repo.head.commit.diff(None)],
            'untracked_files': repo.untracked_files,
            'diff_vs_head': repo.git.diff(repo.head.commit.tree)}


def repo_state_string(repo, detail=1):
    """
    Create a string representation of the repo state with the desired level of detail

    :param repo: the repository to summarize
    :type repo: :class:`git.Repo`

    :param detail: the detail level. See package documentation for details on what each level prints. Default is 1.
    :type default: int

    :return: a string summarizing the repo state
    :rtype: str
    """
    state = list_repo_state(repo)
    status_msg = 'HEAD {sha} ({branch})'.format(sha=state['HEAD'][:7], branch=state['branch'])
    if detail == 0:
        return status_msg
    else:
        modified_files = state['modified_files']
        mod_msg = '{} files modifed'.format(len(modified_files))
        untracked_files = state['untracked_files']
        untr_msg = '{} untracked files'.format(len(untracked_files))

        if detail == 1:
            return '{main} - {mod}, {untracked}'.format(main=status_msg, mod=mod_msg, untracked=untr_msg)
        else:
            listsep = '\n    * '
            mod_list = listsep + listsep.join(modified_files)
            untr_list = listsep + listsep.join(untracked_files)
            status_msg = status_msg + ':\n  ' + mod_msg + mod_list + '\n  ' + untr_msg + untr_list
            if detail > 2:
                diff_msg = state['diff_vs_head']
                status_msg += '\n\n  Difference versus HEAD:\n\n' + diff_msg + '\n\n'

            return status_msg
