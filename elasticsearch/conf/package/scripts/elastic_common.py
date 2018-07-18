#!/usr/bin/env python

"""
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import sys
import os
import glob
from resource_management.core.exceptions import ExecutionFailed
from resource_management.core.resources.system import Execute, File
from resource_management.libraries.functions.format import format
from resource_management.libraries.functions.get_user_call_output import get_user_call_output
from resource_management.libraries.functions.show_logs import show_logs


def kill_process(pid_file, user, log_dir):
    import params
    """
    Kill the process by pid file, then check the process is running or not. If the process is still running after the kill
    command, it will try to kill with -9 option (hard kill)
    """
    pid = get_user_call_output(format("cat {pid_file}"), user=user, is_checked_call=False)[1]
    process_id_exists_command = format("ls {pid_file} >/dev/null 2>&1 && ps -p {pid} >/dev/null 2>&1")

    kill_cmd = format("kill {pid}")
    Execute(kill_cmd,
            not_if=format("! ({process_id_exists_command})"))
    wait_time = 5

    hard_kill_cmd = format("kill -9 {pid}")
    Execute(hard_kill_cmd,
            not_if=format("! ({process_id_exists_command}) || ( sleep {wait_time} && ! ({process_id_exists_command}) )"),
            ignore_failures=True)
    try:
        Execute(format("! ({process_id_exists_command})"),
                tries=20,
                try_sleep=3,
                )
    except:
        show_logs(log_dir, user)
        raise

    File(pid_file,
         action="delete"
         )


def env_setup():
    # setup limits
    with open("/etc/security/limits.conf", "r") as f:
        limits = True
        lines = f.readlines()
        for line in lines:
            if "elasticsearch" in line:
                limits = False
                break
        if limits:
            cmd = format('echo "elasticsearch        -       nofile          65536" >> /etc/security/limits.conf')
            Execute(cmd, user="root")
            cmd = format('echo "elasticsearch        -       nproc           4096" >> /etc/security/limits.conf')
            Execute(cmd, user="root")
            cmd = format('echo "elasticsearch soft memlock unlimited " >> /etc/security/limits.conf')
            Execute(cmd, user="root")
            cmd = format('echo "elasticsearch hard memlock unlimited " >> /etc/security/limits.conf')
            Execute(cmd, user="root")
    # setup vm.max_map_count
    try:
        cmd = format('sysctl -w vm.max_map_count=262144')
        Execute(cmd, user="root")
    except ExecutionFailed, e:
        print e
    if os.path.exists("/etc/sysctl.conf"):
        with open("/etc/sysctl.conf", "r") as f:
            max_map_count = True
            lines = f.readlines()
            for line in lines:
                if "vm.max_map_count" in line:
                    max_map_count = False
                    break
            if max_map_count:
                cmd = format('echo "vm.max_map_count=262144" >> /etc/sysctl.conf')
                Execute(cmd, user="root")
