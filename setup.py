from setuptools import setup

setup(
    name='GitState',
    version='0.1',
    packages=['gitstate'],
    url='https://github.com/joshua-laughner/PyGitState',
    license='',
    author='Joshua Laughner',
    author_email='jllacct119@gmail.com',
    install_requires=['gitpython'],
    description='A package to list the state of all imported packaged under Git VCS'
)
