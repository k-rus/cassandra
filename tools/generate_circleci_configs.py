#!/usr/bin/python
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# This Python program helps to reduce manual steps for running Python's DTests 
# in CircleCI. It takes list of Cassandra branches to run DTests against, the 
# dtest repo fork and branch and optionally, which test to repeat and 
# with/without vnodes or both. It creates new branch and commit for each 
# provided Cassandra branch and each vnodes configuration if both need to be tested.
# Then it pushes the branches to remote `origin`. Thus it is possible to see them
# in CircleCI and approve for execution.
#
# Requires: GitPython 
#
# Currently it is assumed that it is called from the Cassandra repo location.
# It also assumes that there is no pending changes
#
# Run `python generate_circleci_configs.py --help` to get list of arguments and
# descriptions.
#
# Example:
#
# python ../tools/generate_circleci_configs.py --dtest-repo \
# git://github.com/k-rus/cassandra-dtest.git --dtest-branch cass-14196 \
# --dtest-test replace_address_test.py::test_multi_dc_replace_with_rf1 --vnodes all \
# --cassandra-branches cassandra-4.0 cassandra-3.11 cassandra-3.0 trunk \
# --remote upstream
#
# As result it will create and push branches:
# cassandra-3.0-cass-14196-novnodes
# cassandra-3.0-cass-14196-vnodes
# cassandra-3.11-cass-14196-novnodes
# cassandra-3.11-cass-14196-vnodes
# cassandra-4.0-cass-14196-novnodes
# cassandra-4.0-cass-14196-vnodes
# trunk-cass-14196-novnodes
# trunk-cass-14196-vnodes
#
# Each branch will contain one commit over the base branch, which was fetched from
# remote `upstream`, and the commit will contain following changes to 
# `.circleci\config.yml`:
# - use MID resources 
# - use provided dtest repo fork 
# - use provided dtest branch 
# - repeat the provided dtest test 
# - use or not vnodes 
# 
# After the dtest patch is merged the branches can be removed by calling it with 
# argument `remove` and dtest branch as it uses as convention.
# 
# Example:
# 
# python ../tools/generate_circleci_configs.py remove --dtest-branch cass-14196
# 
# Deleting cassandra-3.0-cass-14196-novnodes
# Deleting cassandra-3.0-cass-14196-vnodes
# Deleting cassandra-3.11-cass-14196-novnodes
# Deleting cassandra-3.11-cass-14196-vnodes
# Deleting cassandra-4.0-cass-14196-novnodes
# Deleting cassandra-4.0-cass-14196-vnodes 
# Deleting trunk-cass-14196-novnodes
# Deleting trunk-cass-14196-vnodes 
#

import argparse
import git
import subprocess
import sys

from pathlib import Path

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
            self.repo.remotes[self.args.remote].fetch(base_name)
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
        self.repo = git.Repo(Path('.').absolute(), search_parent_directories=True)
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
    the_repo.remove_branches()
    sys.exit()

the_repo.verify_dtest()
the_repo.do_the_job()
