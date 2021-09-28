import argparse
import git
import subprocess
import sys


def is_no_vnodes(args):
    return args.vnodes == 'novnodes' or args.vnodes == 'all'


class CiBranch():
    def __init__(self, crepo, vnodes) -> None:
        self.repo = crepo.repo
        self.args = crepo.args

        self.circleci_folder = crepo.circleci_folder
        self.config = crepo.config

        self.vnodes = vnodes and self.args.dtest_test

    def create_ci_branch_name(self):
        if self.vnodes:
            vnodes = 'vnodes'
        else:
            vnodes = 'novnodes'
        return self.base_name+'-'+self.args.dtest_branch+'-'+vnodes

    def create_branch(self, base_name):
        self.base_name = base_name
        if (self.args.remote):
            self.branch_name = self.create_ci_branch_name()
            self.repo.create_head(
                self.branch_name, self.repo.remotes[self.args.remote].refs[base_name]).checkout()
        else:
            self.branch_name = base_name
            self.repo.refs[base_name].checkout()

    def generate_config(self):
        comm = [self.circleci_folder + "generate.sh"]
        comm.append("-m")
        comm.append("-e")
        comm.append("DTEST_REPO="+self.args.dtest_repo)
        comm.append("-e")
        comm.append("DTEST_BRANCH="+self.args.dtest_branch)

        if self.args.dtest_test:
            comm.append("-e")
            comm.append("REPEATED_DTEST_NAME=" + self.args.dtest_test)

        if self.vnodes:
            comm.append("-e")
            comm.append("REPEATED_DTEST_VNODES=true")

        subprocess.check_call(comm, cwd=self.circleci_folder)

    def commit(self):
        message = ('DO NOT MERGE! CircleCI configuration for '+self.args.dtest_branch+' and ' +
                   self.base_name)
        if self.vnodes:
            message = message + ' with vnodes'
        else:
            message = message + ' without vnodes'
        self.repo.git.add(self.config)
        self.repo.git.commit('-m', message)

    def push(self):
        self.repo.git.push('-u', 'origin', self.branch_name)


class CassandraRepo():
    def __init__(self, args) -> None:
        self.args = args
        self.repo = git.Repo('/Users/ruslanfomkin/GitRepos/apache/cassandra')
        self.original_ref = self.repo.head.reference
        self.original_branch = self.repo.head.name

        self.circleci_folder = self.repo.working_dir+'/.circleci/'
        self.config = self.circleci_folder + 'config.yml'

    def one_branch(self, cass_branch, vnodes):
        branch = CiBranch(self, vnodes)
        branch.create_branch(cass_branch)
        print(branch.branch_name)
        branch.generate_config()
        branch.commit()
        branch.push()

    def do_the_job(self):
        if self.repo.is_dirty():
            raise ValueError('Uncommitted changes in the git repo. Cannot continue.')

        try:
            for cass_branch in args.cassandra_branches:
                self.one_branch(cass_branch, not is_no_vnodes(self.args))
                if self.args.vnodes == 'all' and self.args.dtest_test:
                    self.one_branch(cass_branch, True)
                self.original_ref.checkout()
        except:
            self.original_ref.checkout()
            raise

    def verify_dtest(args):
        """
        Verifies provided dtest repo and branch
        """
        pass

    def remove_branches(self):
        for branch in self.repo.branches:
            if self.args.dtest_branch in branch.name:
                print('Deleting '+branch.name)
                self.repo.git.push('-d', self.repo.remotes.origin, branch)
                self.repo.git.branch('-D', branch)


parser = argparse.ArgumentParser()
parser.add_argument('--dtest-repo', type=str, help='Name of dtest repository')
parser.add_argument('--dtest-branch', type=str,
                    help='Name of the branch in dtest repository to run')
parser.add_argument('--dtest-test', type=str, help='Name of PyTest test to repeat')
parser.add_argument('--vnodes', choices=['vnodes', 'novnodes', 'all'],
                    help='Run dtest with or without vnodes or both', default='all')
parser.add_argument('--cassandra-branches', nargs='*', type=str)
parser.add_argument(
    '--remote', type=str,
    help='Name of git remote in cassandra repo. By default, use local branches')

parser.add_argument('remove', nargs='?')

args = parser.parse_args()
the_repo = CassandraRepo(args)

if args.remove:
    print('Removing '+args.dtest_branch)
    the_repo.remove_branches()
    sys.exit()

the_repo.verify_dtest()
the_repo.do_the_job()
