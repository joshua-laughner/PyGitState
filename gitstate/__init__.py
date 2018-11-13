"""
gitstate: package to systematically list the state of imported packages under Git version control.

To ensure traceability in scientific results, it is helpful to know, as close as possible, the exact state of code that
produced figures or data. This package is meant to help with that.

Scenario 1: you're making plots in a Jupyter notebook and want to include information about the state of imported
packages used to make those figures::

    from gitstate import print_repos

    ... make plots ...

    print_repos()

This will print, to standard output, a list of imported packages under Git version control, giving the package name,
current HEAD SHA256 hash, current branch, and numbers of untracked and modified files.


Scenario 2: you're generating intermediate data and want a record of the exact state of the repositories used to create
that data::

    from gitstatus import get_repo_states

    ... make data ...

    repo_states = get_repo_state()

    # This is a stand-in for however you'd save the data
    save( data, repo_states )

In this second example, ``repo_states`` will be a dictionary with keys equal to the package name, and values each a
dictionary storing the full HEAD sha256, the current branch name, the lists of untracked and modified files, and the
actual difference of the working directory vs. the HEAD (as a string).


Both of these will, internally, search _all_ imported packages/modules/classes/functions to see if they belong to a Git
repository on your Python path. This should exclude packages installed from PyPI, and assumes that the packages you
want to print the state of are ones you've installed to your system Python or environment by cloning or creating the
desired Git repository, then in the directory with the ``setup.py`` file, doing one of the following::

      python setup.py install [--user]
      python setup.py develop
      pip install [-e] [-user] .

Under these assumptions, any of the functions in gitstate should automatically find these packages if they are imported.

For any functions in the top level of this repo that take a ``detail`` parameter, this controls how much information, is
included in the output:

    0: Only the HEAD SHA256 and the branch name
    1: Level 0 plus the number of untracked and modified files
    2: Level 1 plus the list of untracked and modified files
    3: Level 2 plus the actual diff of the working directory against the HEAD.
"""

from . import repo_utils

#TODO: how to deal with subrepos?
# I've got it working that it'll at least find the parent repo, but it prints with the subrepo's package name.
# Two possibilities:
#   a) make it so that the containing project, whether it's a package or not, is what gets printed
#   b) filter the results to just the subrepo files, probably with a wrapper class around the repo, but then how to
#      avoid double printing them from the parent project?

def print_repos(detail=1):
    """
    Print the state of all imported packages' repos to standard output.

    :param detail: optional, default is 1. Controls amount of information printed. See module help for the specific
     levels.
    :type detail: int

    :return: None
    """
    repos = repo_utils.list_imported_repos()
    for name, repo in repos.items():
        status = repo_utils.repo_state_string(repo, detail=detail)
        print(name + ': ' + status)


def save_states_to_file(filename, detail=3):
    """
    Write the repo states to the given file.

    :param filename: the path of the file to write to. Will be overwritten if exists.
    :type filename: str

    :param detail: optional, default is 3. Controls amount of information printed. See module help for the specific
     levels.
    :type detail: int

    :return: None
    """
    with open(filename, 'w') as fobj:
        repos = repo_utils.list_imported_repos()
        for name, repo in repos.items():
            status = repo_utils.repo_state_string(repo, detail=detail)
            fobj.write(name + ': ' + status + '\n')


def get_repo_states():
    """
    Get a dictionary describing the states of all imported packages' repos.

    :return: dictionary with package names as keys and subdicts describing the state as values.
    :rtype: dict
    """
    repos = repo_utils.list_imported_repos()
    return {name: repo_utils.list_repo_state(repo) for name, repo in repos.items()}
