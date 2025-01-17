# coding: utf-8

"Shared metatests integration tools."

import os
import io
import re
import shutil
import hashlib
import logging

import exts.fs
import exts.windows
from test import const

from yalibrary.loggers.file_log import TokenFilterFormatter


logger = logging.getLogger(__name__)

# Used to remove mutable substrings from an stderr.
cleanup_regex = re.compile(
    r"""(
        (\d+.\d+(s|\ssec))|  # time
        (\d+\sms)|  # time
        (\d\d\:\d\d\:\d\d)|  # time
        (\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})|  # date from rtmr_logpusher
        (\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}.\d{3})|  # timestamp from syn_synpool_test
        ([0-9a-f]+-[0-9a-f]+-[0-9a-f]+-[0-9a-f]+)|  # guid
        (RSS=\d+M)|  # from querydata_indexer
        (\swork\:\s\d+)|  # from rus_fio
        (\d+m\s\d+s)|  # from mr_trie_test
        (\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{3}\s[\+\-]\d{4})|  # from syn_synpool_test
        (sandbox(-middle)?\d+(\.yandex\.ru)?)|  # sandbox host from syn_synpool_test
        (\d+\.\d+\.\d+\.\d+(\:\d+)?)|  # endpoint from syn_synpool_test
        (pid\s+\=\s+\d+)|  # pid from syn_synpool_test
        (serialized\s+\=\s+[0-9A-Z]+)|  # serialized from syn_synpool_test
        (/place/sandbox\-data/srcdir/arcadia_cache[^/]*/)|  # arcadia cache path
        (\[\d+\.\d+\]\s+seconds)|  # time from mtd
        (MRRPL_START[\r\n]+[A-Z0-9]+[\r\n]+MRRPL_END)|  # from objects_and_diversity_cleancache
        (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})|  # from objects_and_diversity_cleancache
        (0x[0-9a-f]{8,})|  # from test_makepool
        (\[([0-9a-f]{1,4}\:){7}[0-9a-f]{1,4}\]\:\d+)|  # simplified IPv6 endpoint from syn_synpool_test
        ([\w\-\.]+\.yandex\.(ru|net))  # from ip2backend_ut
    )""",
    re.VERBOSE,
)


def hash_path(path, cleanup=False, debug_path=None):
    """
    Hash file content
    """

    content = open(path, "rb").read()
    if cleanup:
        content = cleanup_regex.sub("", content)
    if debug_path:
        # Used to debug "output changed" false positives.
        # projects.sandboxsdk.paths.make_folder(os.path.dirname(debug_path))
        open(debug_path, "wb").write(content)
    return hashlib.sha1(content).hexdigest()


def append_python_paths(env, paths, overwrite=False):
    """
    Appends PYTHONPATH in the given env
    :param env: environment dict to be updated
    :param paths: paths to update
    """
    python_path_key = 'PYTHONPATH'
    python_paths = []
    if python_path_key in env and not overwrite:
        python_paths.append(env[python_path_key])
    python_paths.extend(paths)

    env[python_path_key] = os.pathsep.join(python_paths)


def get_python_paths(env):
    return env.get("PYTHONPATH", "").split(os.pathsep)


def get_common_logging_file_handler(path, mode="a"):
    """
    Get a common for test logs logging file handler
    :param path: path to the log file
    :param mode: file open mode
    :return: logging file handler
    """
    file_handler = logging.FileHandler(path, mode=mode)
    file_handler.setFormatter(
        TokenFilterFormatter("%(asctime)s - %(levelname)s - %(name)s - %(funcName)s: %(message)s")
    )
    file_handler.setLevel(logging.DEBUG)
    return file_handler


def link_dir(src, dst):
    """
    Links directory, choosing the best platform approach
    """

    if exts.windows.on_win():
        return exts.fs.hardlink_tree(src, dst)
    return exts.fs.symlink(src, dst)


def link_file(src, dst):
    """
    Links directory, choosing the best platform approach
    """
    if exts.windows.on_win():
        return exts.fs.hardlink_or_copy(src, dst)
    return exts.fs.symlink(src, dst)


def copy_dir_contents(src_dir, dest_dir, ignore_list=[], skip_links=True):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for entry in os.listdir(src_dir):
        if entry in ignore_list:
            continue

        src = os.path.join(src_dir, entry)
        dst = os.path.normpath(os.path.join(dest_dir, entry))

        if os.path.islink(src) and skip_links:
            continue

        if os.path.isdir(src):
            copy_dir_contents(src, dst, ignore_list)

        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy(src, dst)


def get_log_results_link(opts):
    resource_results_id = getattr(opts, "build_results_resource_id", None)
    if resource_results_id:
        return "http://proxy.sandbox.yandex-team.ru/" + resource_results_id
    return None


def get_results_root(opts):
    log_result_link = get_log_results_link(opts)
    output_root = opts and opts.output_root
    if log_result_link or output_root:
        return log_result_link or output_root
    else:
        if opts and getattr(opts, "create_symlinks"):
            return opts.symlink_root or "$(SOURCE_ROOT)"
    return None


def truncate_tail(filename, size):
    if os.stat(filename).st_size <= size:
        return
    with open(filename, 'r+') as afile:
        afile.truncate(size)


def truncate_middle(filename, size, msg=None):
    """
    Truncates file from the middle to the specified size
    """
    msg = "..." if msg is None else msg
    filesize = os.stat(filename).st_size
    if filesize <= size:
        return

    data = msg
    msgsize = len(msg)
    if msgsize < size:
        lend = size // 2 - msgsize // 2
    else:
        lend = size // 2
    with io.open(filename, "r+", errors='ignore') as afile:  # XXX until moved to py3
        if msgsize < size - lend:
            rsize = size - lend - msgsize
        else:
            rsize = size - lend
        rstart = filesize - rsize

        afile.seek(rstart, os.SEEK_SET)
        data += afile.read(rstart)

        afile.seek(lend, os.SEEK_SET)
        afile.write(data)
        afile.truncate(size)


def truncate_logs(files, size):
    for filename in files:
        truncate_middle(filename, size, msg="\n[..truncated..]\n")


def remove_links(dir_path):
    for root, dirs, files in os.walk(dir_path):
        for file_path in files + dirs:
            file_path = os.path.join(root, file_path)
            if os.path.islink(file_path):
                logging.debug("Removing symlink %s", file_path)
                exts.fs.ensure_removed(file_path)


def get_test_tool_path(opts, global_resources, run_on_target):
    local_const_name = const.TEST_TOOL_TARGET_LOCAL if run_on_target else const.TEST_TOOL_HOST_LOCAL
    resource_const_name = const.TEST_TOOL_TARGET if run_on_target else const.TEST_TOOL_HOST
    path = '{}/test_tool'.format(global_resources.get(resource_const_name, '$({})'.format(resource_const_name)))
    if opts and local_const_name in opts.flags:
        path = opts.flags[local_const_name]
    assert path, local_const_name
    return path


def get_wine64_path(global_resources):
    return '{}/bin/wine64'.format(global_resources.get(const.WINE_TOOL, '$({})'.format(const.WINE_TOOL)))


def get_wine32_path(global_resources):
    return '{}/bin/wine'.format(global_resources.get(const.WINE32_TOOL, '$({})'.format(const.WINE32_TOOL)))


def get_test_tool_cmd(opts, tool_name, global_resources, wrapper=False, run_on_target_platform=False, python=None):
    cmd = [
        get_test_tool_path(
            opts, global_resources, run_on_target_platform and const.TEST_TOOL_TARGET in global_resources
        ),
        tool_name,
    ]
    target_tools = getattr(opts, "profile_test_tool", [])
    if target_tools and tool_name in target_tools:
        if wrapper:
            cmd.append("--profile-wrapper")
        else:
            cmd.append("--profile-test-tool")
    return cmd


def get_corpus_data_path(project_path, root=None):
    if "YA_TEST_CORPUS_DATA_PATH" in os.environ:
        target = os.environ.get("YA_TEST_CORPUS_DATA_PATH")
    else:
        target = os.path.join(const.CORPUS_DATA_ROOT_DIR, project_path, const.CORPUS_DATA_FILE_NAME)

    if root:
        return os.path.join(root, target)
    return target


def get_coverage_push_tool(opts, global_resources):
    if opts and const.COVERAGE_PUSH_TOOL_LOCAL in opts.flags:
        return opts.flags[const.COVERAGE_PUSH_TOOL_LOCAL]
    return '{}/cov2lb'.format(
        global_resources.get(const.COVERAGE_PUSH_TOOL_LB_RESOURCE, '$({})'.format(const.COVERAGE_PUSH_TOOL_LB_RESOURCE))
    )
