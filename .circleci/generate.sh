#!/bin/sh
#
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

BASEDIR=`dirname $0`

die ()
{
  echo "ERROR: $*"
  echo "Usage: $0 [-l|-m|-h|-e]"
  echo "   -l Generate config.yml using low resources"
  echo "   -m Generate config.yml using mid resources"
  echo "   -h Generate config.yml using high resources"
  echo "   -e <key=value> Enviroment variables to be used in the generated config.yml, e.g.:"
  echo "                   -e DTEST_BRANCH=CASSANDRA-8272"
  echo "                   -e DTEST_REPO=git://github.com/adelapena/cassandra-dtest.git"
  echo "                   -e REPEATED_UTEST_CLASS=org.apache.cassandra.cql3.ViewTest"
  echo "                   -e REPEATED_UTEST_METHODS=testCompoundPartitionKey,testStaticTable"
  echo "                   -e REPEATED_UTEST_COUNT=100"
  echo "                  If you want to specify multiple environment variables simply add"
  echo "                  multiple -e options. The flags -l/-m/-h should be used when using -e."
  echo "   -f Stop checking that the enviroment variables are known"
  echo "   No flags generates the default config.yml using low resources and the three"
  echo "   templates (config.yml.LOWRES, config.yml.MIDRES and config.yml.HIGHRES)"
  exit 1
}

lowres=false
midres=false
highres=false
envvars=""
check_envvars=true
while getopts "e:lmhf" opt; do
  case $opt in
      l ) ($midres || $highres) && die "Cannot specify option -l after specifying options -m or -h"
          lowres=true
          ;;
      m ) ($lowres || $highres) && die "Cannot specify option -m after specifying options -l or -h"
          midres=true
          ;;
      h ) ($lowres || $midres) && die "Cannot specify option -h after specifying options -l or -m"
          highres=true
          ;;
      e ) !($lowres || $midres || $highres) && die "Cannot specify option -e without first specifying options -l, -m or -h"
          if [ "x$envvars" = "x" ]; then
            envvars="$OPTARG"
          else
            envvars="$envvars|$OPTARG"
          fi
          ;;
      f ) check_envvars=false
          ;;
      \?) die "Invalid option: -$OPTARG"
          ;;
  esac
done

if $lowres; then
  echo "Generating new config.yml file with low resources from config-2_1.yml"
  circleci config process $BASEDIR/config-2_1.yml > $BASEDIR/config.yml.LOWRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.LOWRES.tmp > $BASEDIR/config.yml
  rm $BASEDIR/config.yml.LOWRES.tmp

elif $midres; then
  echo "Generating new config.yml file with middle resources from config-2_1.yml"
  patch -o $BASEDIR/config-2_1.yml.MIDRES $BASEDIR/config-2_1.yml $BASEDIR/config-2_1.yml.mid_res.patch
  circleci config process $BASEDIR/config-2_1.yml.MIDRES > $BASEDIR/config.yml.MIDRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.MIDRES.tmp > $BASEDIR/config.yml
  rm $BASEDIR/config-2_1.yml.MIDRES $BASEDIR/config.yml.MIDRES.tmp

elif $highres; then
  echo "Generating new config.yml file with high resources from config-2_1.yml"
  patch -o $BASEDIR/config-2_1.yml.HIGHRES $BASEDIR/config-2_1.yml $BASEDIR/config-2_1.yml.high_res.patch
  circleci config process $BASEDIR/config-2_1.yml.HIGHRES > $BASEDIR/config.yml.HIGHRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.HIGHRES.tmp > $BASEDIR/config.yml
  rm $BASEDIR/config-2_1.yml.HIGHRES $BASEDIR/config.yml.HIGHRES.tmp

else
  echo "Generating new config.yml file with low resources and LOWRES/MIDRES/HIGHRES templates from config-2_1.yml"

  # setup lowres
  circleci config process $BASEDIR/config-2_1.yml > $BASEDIR/config.yml.LOWRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.LOWRES.tmp > $BASEDIR/config.yml.LOWRES
  rm $BASEDIR/config.yml.LOWRES.tmp

  # setup midres
  patch -o $BASEDIR/config-2_1.yml.MIDRES $BASEDIR/config-2_1.yml $BASEDIR/config-2_1.yml.mid_res.patch
  circleci config process $BASEDIR/config-2_1.yml.MIDRES > $BASEDIR/config.yml.MIDRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.MIDRES.tmp > $BASEDIR/config.yml.MIDRES
  rm $BASEDIR/config-2_1.yml.MIDRES $BASEDIR/config.yml.MIDRES.tmp

  # setup highres
  patch -o $BASEDIR/config-2_1.yml.HIGHRES $BASEDIR/config-2_1.yml $BASEDIR/config-2_1.yml.high_res.patch
  circleci config process $BASEDIR/config-2_1.yml.HIGHRES > $BASEDIR/config.yml.HIGHRES.tmp
  cat $BASEDIR/license.yml $BASEDIR/config.yml.HIGHRES.tmp > $BASEDIR/config.yml.HIGHRES
  rm $BASEDIR/config-2_1.yml.HIGHRES $BASEDIR/config.yml.HIGHRES.tmp

  # copy lower into config.yml to make sure this gets updated
  cp $BASEDIR/config.yml.LOWRES $BASEDIR/config.yml
fi

# replace environment variables
IFS='='
echo "$envvars" | tr '|' '\n' | while read entry; do
  set -- $entry
  key=$1
  val=$2
  if $check_envvars &&
     [ "$key" != "DTEST_REPO" ] &&
     [ "$key" != "DTEST_BRANCH" ] &&
     [ "$key" != "REPEATED_UTEST_TARGET" ] &&
     [ "$key" != "REPEATED_UTEST_CLASS" ] &&
     [ "$key" != "REPEATED_UTEST_METHODS" ] &&
     [ "$key" != "REPEATED_UTEST_COUNT" ] &&
     [ "$key" != "REPEATED_UTEST_STOP_ON_FAILURE" ] &&
     [ "$key" != "REPEATED_DTEST_NAME" ] &&
     [ "$key" != "REPEATED_DTEST_VNODES" ] &&
     [ "$key" != "REPEATED_DTEST_COUNT" ] &&
     [ "$key" != "REPEATED_DTEST_STOP_ON_FAILURE" ] &&
     [ "$key" != "REPEATED_UPGRADE_DTEST_NAME" ] &&
     [ "$key" != "REPEATED_UPGRADE_DTEST_COUNT" ] &&
     [ "$key" != "REPEATED_UPGRADE_DTEST_STOP_ON_FAILURE" ] &&
     [ "$key" != "REPEATED_JVM_UPGRADE_DTEST_CLASS" ] &&
     [ "$key" != "REPEATED_JVM_UPGRADE_DTEST_METHODS" ] &&
     [ "$key" != "REPEATED_JVM_UPGRADE_DTEST_COUNT" ] &&
     [ "$key" != "REPEATED_JVM_UPGRADE_DTEST_STOP_ON_FAILURE" ]; then
    die "Unrecognised environment variable name: $key"
  fi
  echo "Setting environment variable $key: $val"
  sed -i '' "s|- $key:.*|- $key: $val|" $BASEDIR/config.yml
done
unset IFS

