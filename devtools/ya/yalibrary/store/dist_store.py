import six
import time

from core import report
from exts.timer import AccumulateTime

import logging

logger = logging.getLogger(__name__)


class DistStore(object):
    def __init__(self, name, stats_name, tag, readonly, fits_filter=None):
        self._readonly = readonly
        self._timers = {'has': 0, 'put': 0, 'get': 0, 'get-meta': 0}
        self._time_intervals = {'has': [], 'put': [], 'get': [], 'get-meta': []}
        self._counters = {'has': 0, 'put': 0, 'get': 0, 'get-meta': 0}
        self._failures = {'has': 0, 'put': 0, 'get': 0, 'get-meta': 0}
        self._data_size = {'put': 0, 'get': 0}
        self._cache_hit = {'requested': 0, 'found': 0}
        self._meta = {}
        self._name = name
        self._stats_name = stats_name
        self._tag = tag
        self._fits_filter = fits_filter

    def _inc_time(self, x, tag):
        cur_time = time.time()
        self._timers[tag] += x
        self._time_intervals[tag].append((cur_time - x, cur_time))
        self._counters[tag] += 1

    def _count_failure(self, tag):
        self._failures[tag] += 1

    def _inc_data_size(self, size, tag):
        self._data_size[tag] += size

    def fits(self, node):
        raise NotImplementedError()

    def load_meta(self, uids, heater_mode=False, refresh_on_read=False):
        raise NotImplementedError()

    def _do_has(self, uid):
        raise NotImplementedError()

    def has(self, *args, **kwargs):
        with AccumulateTime(lambda x: self._inc_time(x, 'has')):
            return self._do_has(*args, **kwargs)

    def _do_put(self, uid, root_dir, files, codec=None):
        raise NotImplementedError()

    def put(self, *args, **kwargs):
        with AccumulateTime(lambda x: self._inc_time(x, 'put')):
            return self._do_put(*args, **kwargs)

    def _do_try_restore(self, uid, into_dir, filter_func=None):
        raise NotImplementedError()

    def try_restore(self, *args, **kwargs):
        with AccumulateTime(lambda x: self._inc_time(x, 'get')):
            return self._do_try_restore(*args, **kwargs)

    def avg_compression_ratio(self):
        raise NotImplementedError()

    def readonly(self):
        return self._readonly

    def _get_real_time(self, key):
        if not self._time_intervals[key]:
            return 0.0
        # Merge overlapped intervals
        BEG, END = 0, 1
        intervals = sorted(self._time_intervals[key])
        merged = intervals[:1]
        for ti in intervals[1:]:
            last_ti = merged[-1]
            if last_ti[END] >= ti[BEG]:
                b = min(ti[BEG], last_ti[BEG])
                e = max(ti[END], last_ti[END])
                merged[-1] = (b, e)
            else:
                merged.append(ti)

        return sum(ti[END] - ti[BEG] for ti in merged)

    def stats(self, execution_log, evlog_writer):
        for k, v in six.iteritems(self._data_size):
            stat_dict = {'data_size': v, 'type': self._name}
            report.telemetry.report('{}-{}-data-size'.format(self._stats_name, k), stat_dict)
            execution_log['$({}-{}-data-size)'.format(self._name, k)] = stat_dict
        execution_log['$({}-cache-hit)'.format(self._name)] = self._cache_hit

        for k, v in six.iteritems(self._timers):
            real_time = self._get_real_time(k)

            stat_dict = {
                'count': self._counters[k],
                'failures': self._failures[k],
                'prepare': '',
                'timing': (0, real_time),
                'total_time': True,
                'type': self._name,
                'real_time': real_time,
            }
            report.telemetry.report('{}-{}'.format(self._stats_name, k), stat_dict)
            execution_log["$({}-{})".format(self._name, k)] = stat_dict
        if evlog_writer:
            stats = {
                'cache_hit': self._cache_hit,
                'put': {
                    'count': self._counters['put'],
                    'data_size': self._data_size['put'],
                },
                'get': {
                    'count': self._counters['get'],
                    'data_size': self._data_size['get'],
                },
            }
            evlog_writer('stats', **stats)

    def tag(self):
        if self._tag is None:
            raise ValueError()
        return self._tag
