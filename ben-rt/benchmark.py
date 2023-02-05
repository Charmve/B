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
import csv
import collections
import datetime
import os
import subprocess
import sys
import hashlib
import re
import shutil
import collections
import tempfile
import git
import utils.logger as logger
import utils.json_profiles_merger_lib as json_profiles_merger_lib
import utils.output_handling as output_handling

from absl import app
from absl import flags

from utils.values import Values
from utils.bazel import Bazel
from utils.benchmark_config import BenchmarkConfig

# BB_ROOT has different values, depending on the platform.
BB_ROOT = os.path.join(os.path.expanduser('~/'), '.bazel-bench')

# The path to the directory that stores Bazel clones.
BAZEL_CLONE_BASE_PATH = os.path.join(BB_ROOT, 'bazel-clones')
# The path to the directory that stores project clones.
PROJECT_CLONE_BASE_PATH = os.path.join(BB_ROOT, 'project-clones')
BAZEL_GITHUB_URL = 'https://github.com/bazelbuild/bazel.git'
# The path to the directory that stores the bazel binaries.
BAZEL_BINARY_BASE_PATH = os.path.join(BB_ROOT, 'bazel-bin')
# The path to the directory that stores the output csv (If required).
DEFAULT_OUT_BASE_PATH = os.path.join(BB_ROOT, 'out')
# The default name of the aggr json profile.
DEFAULT_AGGR_JSON_PROFILE_FILENAME = 'aggr_json_profiles.csv'


def _get_clone_subdir(project_source):
  """Calculates a hexdigest of project_source to serve as a unique subdir name."""
  return hashlib.md5(project_source.encode('utf-8')).hexdigest()


def _exec_command(args, shell=False, cwd=None):
  logger.log('Executing: %s' % (args if shell else ' '.join(args)))

  return subprocess.run(
      args,
      shell=shell,
      cwd=cwd,
      check=True,
      stdout=sys.stdout if FLAGS.verbose else subprocess.DEVNULL,
      stderr=sys.stderr if FLAGS.verbose else subprocess.DEVNULL)


def _get_commits_topological(commits_sha_list,
                             repo,
                             flag_name,
                             fill_default=True):
  """Returns a list of commits, sorted by topological order.

  e.g. for a commit history A -> B -> C -> D, commits_sha_list = [C, B]
  Output: [B, C]

  If the input commits_sha_list is empty, fetch the latest commit on branch
  'master'
  of the repo.

  Args:
    commits_sha_list: a list of string of commit SHA digest. Can be long or
      short digest.
    repo: the git.Repo instance of the repository.
    flag_name: the flag that is supposed to specify commits_list.
    fill_default: whether to fill in a default latest commit if none is
      specified.

  Returns:
    A list of string of full SHA digests, sorted by topological commit order.
  """
  #print("===> repo:", repo)
  #print("===> flag_name:", flag_name)
  #print("===> commits_sha_list:", commits_sha_list)
  # if commits_sha_list:
  #   long_commits_sha_set = set(
  #       map(lambda x: _to_long_sha_digest(x, repo), commits_sha_list))
  #   print("===> long_commits_sha_set:", long_commits_sha_set)
  #   sorted_commit_list = []
  #   for c in reversed(list(repo.iter_commits())):
  #     if c.hexsha in long_commits_sha_set:
  #       sorted_commit_list.append(c.hexsha)

  #   print("===> sorted_commit_list:", sorted_commit_list)
    
  #   if len(sorted_commit_list) != len(long_commits_sha_set):
  #     raise ValueError(
  #         "The following commits weren't found in the repo in branch master: %s."
  #         % (long_commits_sha_set - set(sorted_commit_list)))
  #   return sorted_commit_list

  # elif not fill_default:
  #   # If we have some binary paths specified, we don't need to fill in a default
  #   # commit.
  #   return []

  # If no commit specified: take the repo's latest commit.
  latest_commit_sha = repo.commit().hexsha
  logger.log('No %s specified, using the latest one: %s' %
             (flag_name, latest_commit_sha))
  return [latest_commit_sha]


def _get_current_branch_name():
  return subprocess_popen("git rev-parse --abbrev-ref HEAD")[0] 


def _get_current_branch_commit():
  return subprocess_popen("git rev-parse HEAD")[0]


def _to_long_sha_digest(digest, repo):
  """Returns the full 40-char SHA digest of a commit."""
  return repo.git.rev_parse(digest) if len(digest) < 40 else digest


def _setup_project_repo(repo_path, project_source):
  """Returns a path to the cloned repository.

  If the repo_path exists, perform a `git fetch` to update the content.
  Else, clone the project to repo_path.

  Args:
    repo_path: the path to clone the repository to.
    project_source: the source to clone the repository from. Could be a local
      path or an URL.

  Returns:
    A git.Repo object of the cloned repository.
  """
  if os.path.exists(repo_path):
    logger.log('Path %s exists. Updating...' % repo_path)
    repo = git.Repo(repo_path)
    repo.git.fetch('origin')
    #print ("repo value: ", repo)
  else:
    logger.log('Cloning %s to %s...' % (project_source, repo_path))
    repo = git.Repo.clone_from(project_source, repo_path)
    #print ("repo value: ", repo)
    # TODO(zhangwei): add clone progressing

  return repo


def _build_bazel_binary(commit, repo, outroot, platform=None):
  """Builds bazel at the specified commit and copy the output binary to outroot.

  If the binary for this commit already exists at the destination path, simply
  return the path without re-building.

  Args:
    commit: the Bazel commit SHA.
    repo: the git.Repo instance of the Bazel clone.
    outroot: the directory inwhich the resulting binary is copied to.
    platform: the platform on which to build this binary.

  Returns:
    The path to the resulting binary (copied to outroot).
  """
  outroot_for_commit = '%s/%s/%s' % (
      outroot, platform, commit) if platform else '%s/%s' % (outroot, commit)
  destination = '%s/bazel' % outroot_for_commit
  if os.path.exists(destination):
    logger.log('Binary exists at %s, reusing...' % destination)
    return destination

  logger.log('Building Bazel binary at commit %s' % commit)
  repo.git.checkout('-f', commit)

  _exec_command(['bazel', 'build', '//src:bazel'], cwd=repo.working_dir)

  # Copy to another location
  binary_out = '%s/bazel-bin/src/bazel' % repo.working_dir

  if not os.path.exists(outroot_for_commit):
    os.makedirs(outroot_for_commit)
  logger.log('Copying bazel binary to %s' % destination)
  shutil.copyfile(binary_out, destination)
  _exec_command(['chmod', '+x', destination])

  return destination


def _construct_json_profile_flags(out_file_path):
  """Constructs the flags used to collect JSON profiles.

  Args:
    out_file_path: The path to output the profile to.

  Returns:
    A list of string representing the flags.
  """
  return [
      '--experimental_generate_json_trace_profile',
      # '--experimental_profile_cpu_usage', # it is effectively always true.
      # '--experimental_json_trace_compression', # its value is determined by the profile name
      '--profile={}'.format(out_file_path)
  ]


def json_profile_filename(data_directory, bazel_bench_uid, bazel_commit,
                          unit_num, project_commit, run_number, total_runs):
  return (f'{data_directory}/{bazel_bench_uid}_{bazel_commit}_{unit_num}'
          + f'_{project_commit}_{run_number}_of_{total_runs}.profile.gz')


def subprocess_popen(statement):
    p = subprocess.Popen(statement, shell=True, stdout=subprocess.PIPE)  # 执行shell语句并定义输出格式
    while p.poll() is None:  # 判断进程是否结束（Popen.poll()用于检查子进程（命令）是否已经执行结束，没结束返回None，结束后返回状态码）
        if p.wait() != 0:  # 判断是否执行成功（Popen.wait()等待子进程结束，并返回状态码；如果设置并且在timeout指定的秒数之后进程还没有结束，将会抛出一个TimeoutExpired异常。）
            print("命令执行失败，请检查设备连接状态")
            return False
        else:
            re = p.stdout.readlines()  # 获取原始执行结果
            result = []
            for i in range(len(re)):  # 由于原始结果需要转换编码，所以循环转为utf8编码并且去除\n换行
                res = re[i].decode('utf-8').strip('\r\n')
                result.append(res)
            return result


def _single_run(bazel_bin_path,
                command,
                options,
                targets,
                startup_options):
  """Runs the benchmarking for a combination of (bazel version, project version).

  Args:
    bazel_bin_path: the path to the bazel binary to be run.
    command: the command to be run with Bazel.
    options: the list of options.
    targets: the list of targets.
    startup_options: the list of target options.

  Returns:
    A result object:
    {
      'wall': 1.000,
      'cpu': 1.000,
      'system': 1.000,
      'memory': 1.000,
      'exit_status': 0,
      'started_at': datetime.datetime(2019, 1, 1, 0, 0, 0, 000000),
    }
  """
  #logger.log_warn("---> bazel_bin_path: %s" % bazel_bin_path)
  #logger.log_warn("---> startup_options: %s" % startup_options)
  # bazel_bin_path = subprocess_popen("which bazel")[0] # _exec_command is optional
  # logger.log_warn("---> reset bazel_bin_path to : %s" % bazel_bin_path)
  bazel = Bazel(bazel_bin_path, startup_options)

  default_arguments = collections.defaultdict(list)

  # Prepend some default options if the command is 'build'.
  # The order in which the options appear matters.
  if command == 'build':
    options = options + ['--nostamp', '--noshow_progress', '--color=no']
  measurements = bazel.command(command, args=options + targets)

  if measurements != None:
      logger.log('Results of this run: wall: ' +
              '%.3fs, cpu %.3fs, system %.3fs, memory %.3fMB, exit_status: %d' % (
                  measurements['wall'],
                  measurements['cpu'],
                  measurements['system'],
                  measurements['memory'],
                  measurements['exit_status']))

  # Get back to a clean state.
  bazel.command('clean', ['--color=no'])
  bazel.command('shutdown')
  return measurements


def _run_benchmark(bazel_bin_path,
                   project_path,
                   runs,
                   command,
                   options,
                   targets,
                   startup_options,
                   prefetch_ext_deps,
                   bazel_bench_uid,
                   unit_num,
                   data_directory=None,
                   collect_profile=False,
                   bazel_identifier=None,
                   project_commit=None):
  """Runs the benchmarking for a combination of (bazel version, project version).

  Args:
    bazel_bin_path: the path to the bazel binary to be run.
    project_path: the path to the project clone to be built.
    runs: the number of runs.
    bazel_args: the unparsed list of arguments to be passed to Bazel binary.
    prefetch_ext_deps: whether to do a first non-benchmarked run to fetch the
      external dependencies.
    bazel_bench_uid: a unique string identifier of this entire bazel-bench run.
    unit_num: the numerical order of the current unit being benchmarked.
    collect_profile: whether to collect JSON profile for each run.
    data_directory: the path to the directory to store run data. Required if
      collect_profile.
    bazel_identifier: the commit hash of the bazel commit. Required if
      collect_profile.
    project_commit: the commit hash of the project commit. Required if
      collect_profile.

  Returns:
    A list of result objects from each _single_run.
  """
  collected = []
  os.chdir(project_path)

  logger.log('=== BENCHMARKING BAZEL [Unit #%d]: %s, PROJECT: %s ===' %
             (unit_num, bazel_identifier, project_commit))
  # Runs the command once to make sure external dependencies are fetched.
  if prefetch_ext_deps:
    logger.log('Pre-fetching external dependencies...')
    project_run_result=_single_run(bazel_bin_path, command, options, targets, startup_options)
    # print("\n====> project_run_result: ", project_run_result)

  if collect_profile:
    if not os.path.exists(data_directory):
      os.makedirs(data_directory)

  for i in range(1, runs + 1):
    logger.log('Starting benchmark run %s/%s:' % (i, runs))

    maybe_include_json_profile_flags = options[:]
    if collect_profile:
      assert bazel_identifier, ('bazel_identifier is required when '
                                'collect_profile')
      assert project_commit, ('project_commit is required when '
                              'collect_profile')
      maybe_include_json_profile_flags += _construct_json_profile_flags(
          json_profile_filename(
              data_directory=data_directory,
              bazel_bench_uid=bazel_bench_uid,
              bazel_commit=bazel_identifier.replace('/', '_'),
              unit_num=unit_num,
              project_commit=project_commit,
              run_number=i,
              total_runs=runs,
          ))
    collected.append(
        _single_run(bazel_bin_path, command, maybe_include_json_profile_flags,
                    targets, startup_options))

  return collected, (command, targets, options)


def handle_json_profiles_aggr(bazel_bench_uid, unit_num, bazel_commits,
                              project_source, project_commits, runs,
                              output_path, data_directory):
  """Aggregates the collected JSON profiles and writes the result to a CSV.

   Args:
    bazel_bench_uid: a unique string identifier of this entire bazel-bench run.
    unit_num: the numerical order of the current unit being benchmarked.
    bazel_commits: the Bazel commits that bazel-bench ran on.
    project_source: a path/url to a local/remote repository of the project on
      which benchmarking was performed.
    project_commits: the commits of the project when benchmarking was done.
    runs: the total number of runs.
    output_path: the path to the output csv file.
    data_directory: the directory that stores output files.
  """
  output_dir = os.path.dirname(output_path)
  if not os.path.exists(output_dir):
    os.makedirs(output_dir)

  with open(output_path, 'w') as f:
    csv_writer = csv.writer(f)
    csv_writer.writerow([
        'bazel_source', 'project_source', 'project_commit', 'cat', 'name', 'dur'
    ])

    for bazel_commit in bazel_commits:
      for project_commit in project_commits:
        profiles_filenames = [
            json_profile_filename(
                data_directory=data_directory,
                bazel_bench_uid=bazel_bench_uid,
                bazel_commit=bazel_commit,
                unit_num=unit_num,
                project_commit=project_commit,
                run_number=i,
                total_runs=runs,
            )
            for i in range(1, runs + 1)
        ]
        print(profiles_filenames)
        event_list = json_profiles_merger_lib.aggregate_data(
            profiles_filenames, only_phases=True)
        for event in event_list:
          csv_writer.writerow([
              bazel_commit, project_source, project_commit, event['cat'],
              event['name'], event['median']
          ])
  logger.log('Finished writing aggregate_json_profiles to %s' % output_path)


def create_summary(data, project_source):
  """Creates the runs summary onto stdout.

  Excludes runs with non-zero exit codes from the final summary table.
  """
  unit = {
    'wall': 's ',
    'cpu': 's ',
    'system': 's ',
    'memory': 'MB'
  }
  # print_data
  #for key,value in data.items():
  #  print(key,":",value)
  
  summary_builder = []
  summary_builder.append('\n✨ RESULTS:')
  last_collected = None
  bazel_version = subprocess_popen("bazel --version | awk -F ' ' '{print $2}'")[0]
  for (i, bazel_commit, project_commit), collected in data.items():
    header = ('[Unit #%d] Bazel version: %s, Project commit: %s, Project source: %s' %
              (i, bazel_version, project_commit, project_source))
    summary_builder.append(header)

    summary_builder.append(
        '%s  %s %s %s %s' %
        ('metric'.rjust(8), 'mean'.center(20), 'median'.center(20),
         'stddev'.center(10), 'pval'.center(10)))

    summary_builder.append(' %s' % '----------------------------------------------------------------------'.center(68))
    
    num_runs = len(collected['wall'].items())
    #print("====> nums_runs: ", num_runs)
    # A map from run number to exit code, for runs with non-zero exit codes.
    non_zero_runs = {}
    for i, exit_code in enumerate(collected['exit_status'].items()):
      if exit_code != 0:
        non_zero_runs[i] = exit_code
    for metric, values in collected.items():
      if metric in ['exit_status', 'started_at']:
        continue

      values_exclude_failures = values.exclude_from_indexes(
        non_zero_runs.keys())
      # Skip if there's no value available after excluding failed runs.
      if not values_exclude_failures.items():
        continue

      #print("11111====> last_collected:", last_collected)
      #for key,value in last_collected.items():
      #  print("11111====> collected[%s]" % key, value.values())
      if last_collected:
        print("Yes --- ", last_collected)
        base = last_collected[metric]
        pval = '% 7.5f' % values_exclude_failures.pval(base.values())
        mean_diff = '(% +6.2f%%)' % (
            100. * (values_exclude_failures.mean() - base.mean()) / base.mean())
        median_diff = '(% +6.2f%%)' % (
            100. *
            (values_exclude_failures.median() - base.median()) / base.median())
        print("====> base:%s, pval:%s, mean_diff:%s, median_diff: %s" % base.values(), pval, mean_diff, median_diff)
      else:
        pval = ''
        mean_diff = median_diff = '         '
#print("\n===========> \n     pval:" , pval)
#print("    mean_diff:", mean_diff)
#print("    median_diff:" , median_diff)
      summary_builder.append(
          '%s: %s %s %s %s' %
          (metric.rjust(8),
           ('% 8.3f%s %s' %
            (values_exclude_failures.mean(), unit[metric], mean_diff)).center(20),
           ('% 8.3f%s %s' %
            (values_exclude_failures.median(), unit[metric], median_diff)).center(20),
           ('% 7.3f%s' % (values_exclude_failures.stddev(), unit[metric])).center(10),
           pval.center(10)))
    # print("====> summary_builder:", summary_builder)
    last_collected = collected
#print("====> last_collected:")
#for key,value in last_collected.items():
#print("collected[%s]" % key, value.values())
    if non_zero_runs:
      summary_builder.append(
          ('The following runs contain non-zero exit code(s):\n %s\n'
           'Please check the full log for more details. These runs are '
           'excluded from the above result table.' %
           '\n '.join('- run: %s/%s, exit_code: %s' % (k + 1, num_runs, v)
                      for k, v in non_zero_runs.items())))
    summary_builder.append('')

  return '\n'.join(summary_builder)


FLAGS = flags.FLAGS
# Flags for the bazel binaries.
flags.DEFINE_list('bazel_commits', None, 'The commits at which bazel is built.')
flags.DEFINE_list('bazel_binaries', None,
                  'The pre-built bazel binaries to benchmark.')
flags.DEFINE_string('bazel_source',
                    'https://github.com/bazelbuild/bazel.git',
                    'Either a path to the local Bazel repo or a https url to ' \
                    'a GitHub repository.')
flags.DEFINE_string(
    'bazel_bin_dir', None,
    'The directory to store the bazel binaries from each commit.')

# Flags for the project to be built.
flags.DEFINE_string(
    'project_label', None,
    'The label of the project. Only relevant in the daily performance report.')
flags.DEFINE_string('project_source', None,
                    'Either a path to the local git project to be built or ' \
                    'a https url to a GitHub repository.')
flags.DEFINE_list('project_commits', None,
                  'The commits from the git project to be benchmarked.')
flags.DEFINE_string(
    'env_configure', None,
    "The shell commands to configure the project's environment.")

# Execution options.
flags.DEFINE_integer('runs', 5, 'The number of benchmark runs.')
flags.DEFINE_string('bazelrc', None, 'The path to a .bazelrc file.')
flags.DEFINE_string('platform', None,
                    ('The platform on which bazel-bench is run. This is just '
                     'to categorize data and has no impact on the actual '
                     'script execution.'))

# Miscellaneous flags.
flags.DEFINE_boolean('verbose', False,
                     'Whether to include git/Bazel stdout logs.')
flags.DEFINE_boolean('prefetch_ext_deps', True,
                     'Whether to do an initial run to pre-fetch external ' \
                     'dependencies.')
flags.DEFINE_boolean('collect_profile', False,
                     'Whether to collect JSON profile for each run. Requires ' \
                     '--data_directory to be set.')
flags.DEFINE_boolean('aggregate_json_profiles', False,
                     'Whether to aggregate the collected JSON profiles. Requires '\
                     '--collect_profile to be set.')
flags.DEFINE_string(
    'benchmark_config', None,
    'Whether to use the config-file interface to define benchmark units.')

# Output storage flags.
flags.DEFINE_string('data_directory', None,
                    'The directory in which the csv files should be stored.')
# The daily report generation process on BazelCI requires the csv file name to
# be determined before bazel-bench is launched, so that METADATA files are
# properly filled.
flags.DEFINE_string('csv_file_name', None,
                    'The name of the output csv, without the .csv extension.')


def _flag_checks():
  """Verify flags requirements."""
  if (not FLAGS.benchmark_config and FLAGS.bazel_commits and
      FLAGS.project_commits and len(FLAGS.bazel_commits) > 1 and
      len(FLAGS.project_commits) > 1):
    raise ValueError(
        'Either --bazel_commits or --project_commits should be a single element.'
    )

  if FLAGS.aggregate_json_profiles and not FLAGS.collect_profile:
    raise ValueError('--aggregate_json_profiles requires '
                     '--collect_profile to be set.')


def _get_benchmark_config_and_clone_repos(argv):
  """From the flags/config file, get the benchmark units.

  Args:
    argv: the command line arguments.

  Returns:
    An instance of BenchmarkConfig that contains the benchmark units.
  """
  if FLAGS.benchmark_config:
    config = BenchmarkConfig.from_file(FLAGS.benchmark_config)
    project_source = config.get_project_source()
    project_clone_repo = _setup_project_repo(
        PROJECT_CLONE_BASE_PATH + '/' + _get_clone_subdir(project_source),
        project_source)
    bazel_source = config.get_bazel_source()
    bazel_clone_repo = _setup_project_repo(
        BAZEL_CLONE_BASE_PATH + '/' + _get_clone_subdir(bazel_source),
        bazel_source)

    return config, bazel_clone_repo, project_clone_repo

  # Strip off 'benchmark.py' from argv
  # argv would be something like:
  # ['benchmark.py', 'build', '--nobuild', '//:all']
  bazel_args = argv[1:]

  # Building Bazel binaries
  bazel_binaries = FLAGS.bazel_binaries or []
  logger.log('Preparing bazelbuild/bazel repository.')
  bazel_source = FLAGS.bazel_source if FLAGS.bazel_source else BAZEL_GITHUB_URL
  bazel_clone_repo = _setup_project_repo(
        PROJECT_CLONE_BASE_PATH + '/' + _get_clone_subdir(bazel_source),
        bazel_source)
  bazel_commits = _get_commits_topological(
      FLAGS.bazel_commits,
      bazel_clone_repo,
      'bazel_commits',
      fill_default=not FLAGS.bazel_commits and not bazel_binaries)

  # Set up project repo
  logger.log('Preparing %s clone.' % FLAGS.project_source)
  # project_clone_repo = _setup_project_repo(
#    PROJECT_CLONE_BASE_PATH + '/' + _get_clone_subdir(FLAGS.project_source),
#     FLAGS.project_source)
  project_clone_repo = FLAGS.project_source

# project_commits = _get_commits_topological(FLAGS.project_commits,
#                                             project_clone_repo,
#                                             'project_commits')

  config = BenchmarkConfig.from_flags(
      bazel_commits=bazel_commits,
      bazel_binaries=bazel_binaries,
      project_commits=FLAGS.project_commits,
      bazel_source=bazel_source,
      project_source=FLAGS.project_source,
      env_configure=FLAGS.env_configure,
      runs=FLAGS.runs,
      collect_profile=FLAGS.collect_profile,
      command=' '.join(bazel_args))

  return config, bazel_clone_repo, project_clone_repo


def main(argv):
  _flag_checks()

  config, bazel_clone_repo, project_clone_repo = _get_benchmark_config_and_clone_repos(
      argv)

  # A dictionary that maps a (bazel_commit, project_commit) tuple
  # to its benchmarking result.
  data = collections.OrderedDict()
  csv_data = collections.OrderedDict()
  data_directory = FLAGS.data_directory or DEFAULT_OUT_BASE_PATH

  # We use the start time as a unique identifier of this bazel-bench run.
  bazel_bench_uid = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')

  bazel_bin_base_path = FLAGS.bazel_bin_dir or BAZEL_BINARY_BASE_PATH

  # Build the bazel binaries, if necessary.
  for unit in config.get_units():
    if 'bazel_binary' in unit:
      unit['bazel_bin_path'] = unit['bazel_binary']
    elif 'bazel_commit' in unit:
      bazel_bin_path = subprocess_popen("which bazel")[0] # _exec_command is optional
# bazel_bin_path = _exec_command('which bazel')
# bazel_bin_path = "/home/qcraft/.bazel-bench/bazel-bin/ace99b575fe1e43f7591b75cf5d1c867175f9980/bazel"
      # bazel_bin_path = _build_bazel_binary(unit['bazel_commit'],
      #                                     bazel_clone_repo,
      #                                     bazel_bin_base_path, FLAGS.platform)
      unit['bazel_bin_path'] = bazel_bin_path

  for i, unit in enumerate(config.get_units()):
    bazel_identifier = unit['bazel_commit'] if 'bazel_commit' in unit else unit['bazel_binary']
    project_commit = unit['project_commit']

# project_clone_repo.git.checkout('-f', project_commit)
    if unit['env_configure'] is not None:
      _exec_command(
          unit['env_configure'], shell=True, cwd=project_clone_repo.working_dir)

    results, args = _run_benchmark(
        bazel_bin_path=unit['bazel_bin_path'],
# project_path=project_clone_repo.working_dir,
        project_path=project_clone_repo,
        runs=unit['runs'],
        command=unit['command'],
        options=unit['options'],
        targets=unit['targets'],
        startup_options=unit['startup_options'],
        prefetch_ext_deps=FLAGS.prefetch_ext_deps,
        bazel_bench_uid=bazel_bench_uid,
        unit_num=i,
        collect_profile=unit['collect_profile'],
        data_directory=data_directory,
        bazel_identifier=bazel_identifier,
        project_commit=project_commit)
    collected = {} #collections.defaultdict(dic)
    # collected.setdefault('started_at', {}).setdefault('city', {})['down'] = "wang"
    # print("\nbenchmarking_result:")
    for benchmarking_result in results:
      #  print(benchmarking_result)
      for metric, value in benchmarking_result.items():
        #print(metric, value)
        if metric not in collected:
            collected[metric] = Values()
            # print("metric:", metric, ",    Values() ---- ", Values())
        # print("\n======= metric:", metric,   ", value:", value)
        collected[metric].add(value)
        # print("collected[%s].values: " % metric, collected[metric].values())

    print("\n###### collected:")
    # print(collected)
    #for collected_item in collected: 
    #    print(collected_item)

    data[(i, bazel_identifier, project_commit)] = collected
    # print("\n###### data:" , data)
    non_measurables = {
      'project_source': unit['project_source'],
      'platform': FLAGS.platform,
      'project_label': FLAGS.project_label
    }
    csv_data[(bazel_identifier, project_commit)] = {
        'results': results,
        'args': args,
        'non_measurables': non_measurables
    }

  summary_text = create_summary(data, config.get_project_source())
  print("\n============================================================================================================")
  print(summary_text)

  if FLAGS.data_directory:
    csv_file_name = FLAGS.csv_file_name or '{}.csv'.format(bazel_bench_uid)
    txt_file_name = csv_file_name.replace('.csv', '.txt')

    output_handling.export_csv(data_directory, csv_file_name, csv_data)
    output_handling.export_file(data_directory, txt_file_name, summary_text)

    #result_summary_file_name = 'summary_{}'.format(bazel_bench_uid)
    #bench_uids = []
    #output_handling.summary_total_result(data_directory, result_summary_file_name, bench_uids)

    # This is mostly for the nightly benchmark.
    if FLAGS.aggregate_json_profiles:
      aggr_json_profiles_csv_path = (
          '%s/%s' % (FLAGS.data_directory, DEFAULT_AGGR_JSON_PROFILE_FILENAME))
      handle_json_profiles_aggr(
          bazel_bench_uid=bazel_bench_uid,
          unit_num=i,
          bazel_commits=config.get_bazel_commits(),
          project_source=config.get_project_source(),
          project_commits=config.get_project_commits(),
          runs=FLAGS.runs,
          output_path=aggr_json_profiles_csv_path,
          data_directory=FLAGS.data_directory,
      )

  logger.log('Done.')


if __name__ == '__main__':
  app.run(main)
