# Copyright 2019 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Handles Bazel invocations and measures their time/memory consumption."""
import subprocess
import os
import time
import psutil
import datetime
import utils.logger as logger


class Bazel(object):
  """Class to handle Bazel invocations.

  Allows to measure resource consumption of each command.

  Attributes:
    bazel_binary_path: A string specifying the path to the bazel binary to be
      invoked.
    bazelrc: A string specifying the argument to the bazelrc flag. Uses
      /dev/null if not set explicitly.
  """

  def __init__(self, bazel_binary_path, startup_options, platform):
    self._bazel_binary_path = str(bazel_binary_path)
    self._startup_options = startup_options
    self._platform = platform
    self._pid = None

  def command(self, command, args=None):
    """Invokes a command with a bazel binary.

    Args:
      command: A string specifying the bazel command to invoke.
      args: An optional list of strings representing additional arguments to the
        bazel command.

    Returns:
      A dict containing collected metrics (wall, cpu, system times and
      optionally memory), the exit_status of the Bazel invocation, and the
      start datetime (in UTC).
      Returns None instead if the command equals 'shutdown'.
    """
    args = args or []
    result = dict()

    dev_null = open(os.devnull, 'w')
    exit_status = 0

    if self._platform == 'j5': ##  or 'x9' in self._platform:
      #self._bazel_binary_path = 'qbuild'
      if command == 'run':
        command='--run'
      else:
        return None
      logger.log('Executing Bazel command: %s %s %s %s %s' %
             (self._bazel_binary_path, ' '.join(self._startup_options), command, self._platform, args[2]))
      # print(self._bazel_binary_path, command, self._platform, args[2])
      # print([self._bazel_binary_path, self._startup_options, command, self._platform, args[2]])
      try:
        subprocess.check_call(
            [self._bazel_binary_path, command, self._platform, args[2]])
      except subprocess.CalledProcessError as e:
        exit_status = e.returncode
        logger.log_error('QBuild command failed with exit code %s' % e.returncode)
      
      return None

    else:
      result['started_at'] = datetime.datetime.utcnow()
      before_times = self._get_times()

      logger.log('Executing Bazel command: bazel %s %s %s' %
             (' '.join(self._startup_options), command, ' '.join(args)))
      # print([self._bazel_binary_path] + self._startup_options + [command] + args)
      try:
        subprocess.check_call(
            [self._bazel_binary_path] + self._startup_options + [command] + args,
            stdout=dev_null,
            stderr=dev_null)
      except subprocess.CalledProcessError as e:
        exit_status = e.returncode
        logger.log_error('Bazel command failed with exit code %s' % e.returncode)
    
      if command == 'shutdown':
        return None
      after_times = self._get_times()

      for kind in ['wall', 'cpu', 'cpu_user', 'cpu_system']:
        result[kind] = after_times[kind] - before_times[kind]
        # print("%s: " % kind, result[kind])
      result['exit_status'] = exit_status

      # We do a number of runs here to reduce the noise in the data.
      result['memory'] = min([self._get_heap_size() for _ in range(5)])

      return result

  def _get_pid(self):
    """Returns the pid of the server.

    Has the side effect of starting the server if none is running. Caches the
    result.
    """
    if not self._pid:
      self._pid = (int)(
          subprocess.check_output([self._bazel_binary_path] +
                                  self._startup_options +
                                  ['info', 'server_pid']))
    return self._pid

  def _get_times(self):
    """Retrieves and returns the used times."""
    # TODO(twerth): Getting the pid have the side effect of starting up the
    # Bazel server. There are benchmarks where we don't want this, so we
    # probably should make it configurable.
    process_data = psutil.Process(pid=self._get_pid())
    cpu_times = process_data.cpu_times()

    # refe: https://psutil.readthedocs.io/en/latest/#processes
    # https://github1s.com/giampaolo/psutil/blob/master/psutil/_pslinux.py#L586-L587
    print("====> cpu_time:", time.process_time())
    print("====> cpu_num:", process_data.cpu_num())

    return {
        'wall': time.time(),
        # 'cpu': cpu_times.user, #TODO: add domianed cpu core numbers
        # 'cpu': time.process_time(),
        'cpu': sum(cpu_times[:3]),
        'cpu_user': cpu_times.user,
        'cpu_system': cpu_times.system,
    }
  
  def _get_walltime(self):
    return {
        'wall': time.time(),
    }

  def _get_heap_size(self):
    """Retrieves and returns the used heap size."""
    return (int)(
        subprocess.check_output([self._bazel_binary_path] +
                                self._startup_options +
                                ['info', 'used-heap-size-after-gc'])[:-3])
