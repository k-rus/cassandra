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
        self.config_2_1 = crepo.config_2_1
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
        self.branch_name = self.create_ci_branch_name()
        self.repo.create_head(
            self.branch_name, self.repo.remotes['upstream'].refs[base_name]).checkout()

    def on_vnodes(self):
        with open(self.config_2_1, 'r') as file:
            filedata = file.read()
        file_replace = filedata.replace(
            'REPEATED_DTEST_VNODES: false', 'REPEATED_DTEST_VNODES: true')
        with open(self.config_2_1, 'w') as file:
            file.write(file_replace)

    def edit_config(self):
        oss_repo_name = 'DTEST_REPO: git://github.com/apache/cassandra-dtest.git'
        new_string_repo_name = 'DTEST_REPO: '+self.args.dtest_repo

        with open(self.config_2_1, 'r') as file:
            filedata = file.read()
        file_replace = filedata.replace(oss_repo_name, new_string_repo_name)
        file_replace = file_replace.replace(
            'TEST_BRANCH: trunk', 'TEST_BRANCH: '+self.args.dtest_branch)
        if self.args.dtest_test:
            file_replace = file_replace.replace(
                'REPEATED_DTEST_NAME:\n', 'REPEATED_DTEST_NAME: ' + self.args.dtest_test+'\n')
        with open(self.config_2_1, 'w') as file:
            file.write(file_replace)

        if self.vnodes:
            self.on_vnodes()

        subprocess.run(
            [self.circleci_folder + 'generate.sh', '-m'],
            cwd=self.circleci_folder)

    def commit(self):
        message = ('DO NOT MERGE. CircleCI configuration for '+self.args.dtest_branch+' and ' +
                   self.base_name)
        if self.vnodes:
            message = message + ' with vnodes'
        else:
            message = message + ' without vnodes'
        self.repo.git.add(self.config_2_1, self.config)
        self.repo.git.commit('-m', message)

    def push(self):
        origin = self.repo.remotes['origin']
        # self.repo.head.reference.set_tracking_branch(self.repo.head.reference)
        # create remote ref
        self.repo.git.push('-u', 'origin', self.branch_name)


class CassandraRepo():
    def __init__(self, args) -> None:
        self.args = args
        self.repo = git.Repo('/Users/ruslanfomkin/GitRepos/apache/cassandra')
        self.original_ref = self.repo.head.reference
        self.original_branch = self.repo.head.name

        self.circleci_folder = self.repo.working_dir+'/.circleci/'
        self.config_2_1 = self.circleci_folder + 'config-2_1.yml'
        self.config = self.circleci_folder + 'config.yml'

    def do_the_job(self):
        if self.repo.is_dirty():
            raise ValueError('Uncommitted changes in the git repo. Cannot continue.')

        try:
            for cass_branch in args.cassandra_branches:
                branch = CiBranch(self, not is_no_vnodes(self.args))
                branch.create_branch(cass_branch)
                print(branch.branch_name)
                branch.edit_config()
                branch.commit()
                branch.push()
                if self.args.vnodes == 'all' and self.args.dtest_test:
                    vnodes_branch = CiBranch(branch, True)
                    vnodes_branch.create_branch(cass_branch)
                    vnodes_branch.on_vnodes()
                    vnodes_branch.commit()
                    vnodes_branch.push()

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
parser.add_argument('remove', nargs='?')

args = parser.parse_args()
the_repo = CassandraRepo(args)

if args.remove:
    print('Removing '+args.dtest_branch)
    the_repo.remove_branches()
    sys.exit()

the_repo.verify_dtest()
the_repo.do_the_job()
