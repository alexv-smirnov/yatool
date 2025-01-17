import math
import os

import test.common
import test.const
import test.util.shared
import test.util.tools

from test.test_types.py_test import LintTestSuite
from yalibrary.graph.const import BUILD_ROOT, SOURCE_ROOT


class CustomLintTestSuite(LintTestSuite):
    def __init__(self, dart_info, **kwargs):
        super(CustomLintTestSuite, self).__init__(dart_info, **kwargs)
        self._files = self.get_suite_files()
        self._configs = dart_info.get("LINT-CONFIGS", [])
        self._lint_name = dart_info["LINT-NAME"]
        self._linter = dart_info["LINTER"]
        self._file_processing_time = float(dart_info.get("LINT-FILE-PROCESSING-TIME") or "0.0")
        self._extra_params = dart_info.get("LINT-EXTRA-PARAMS", [])

    def support_splitting(self, opts=None):
        return self._file_processing_time > 0

    def get_split_factor(self, opts):
        if opts and opts.testing_split_factor:
            return opts.testing_split_factor

        if self._files and self.support_splitting():
            return int(math.ceil(self._file_processing_time * len(self._files) / self.timeout))
        return 1

    @property
    def cache_test_results(self):
        # suite is considered to be steady
        return True

    @classmethod
    def get_type_name(cls):
        return "custom_lint"

    def get_type(self):
        return self._lint_name

    @property
    def salt(self):
        return self._lint_name + " ".join(self._configs) + ";".join(self._extra_params)

    def get_run_cmd(self, opts, retry=None, for_dist_build=False):
        work_dir = test.common.get_test_suite_work_dir(
            BUILD_ROOT,
            self.project_path,
            self.name,
            retry,
            split_count=self._modulo,
            split_index=self._modulo_index,
            target_platform_descriptor=self.target_platform_descriptor,
            multi_target_platform_run=self.multi_target_platform_run,
            remove_tos=opts.remove_tos,
        )
        cmd = test.util.tools.get_test_tool_cmd(
            opts, "run_custom_lint", self.global_resources, wrapper=True, run_on_target_platform=True
        ) + [
            "--source-root",
            SOURCE_ROOT,
            "--build-root",
            BUILD_ROOT,
            "--project-path",
            os.path.join(SOURCE_ROOT, self.project_path),
            "--trace-path",
            os.path.join(work_dir, test.const.TRACE_FILE_NAME),
            "--out-path",
            os.path.join(work_dir, test.const.TESTING_OUT_DIR_NAME),
            "--lint-name",
            self._lint_name,
            "--linter",
            self._linter,
        ]
        for dep in sorted(self._custom_dependencies):
            cmd += ["--depends", dep]
        for f in opts.tests_filters + self._additional_filters:
            cmd += ["--tests-filters", f]
        for cfg in self._configs:
            cmd += ["--config", os.path.join(SOURCE_ROOT, cfg)]
        for resource in self.get_global_resources():
            cmd += ["--global-resource", resource]
        for extra_param in self._extra_params:
            cmd += ["--extra-param", extra_param]
        cmd += self._get_files(opts)[self._modulo_index :: self._modulo]
        return cmd

    def _get_test_name(self, filename):
        if filename.startswith(SOURCE_ROOT):
            filename = os.path.relpath(filename, SOURCE_ROOT)
        relative_path = os.path.relpath(filename, self.project_path)
        return "{}::{}".format(relative_path, self._lint_name)

    def get_computed_test_names(self, opts):
        return [self._get_test_name(filename) for filename in self._get_files()]

    # TODO YMAKE-427
    def get_arcadia_test_data(self):
        data = super(CustomLintTestSuite, self).get_arcadia_test_data()
        return data + self._configs

    def get_test_dependencies(self):
        return list(set([x for x in self.dart_info.get('CUSTOM-DEPENDENCIES', '').split(' ') if x]))
