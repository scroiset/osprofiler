# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import collections
import threading
import uuid

from osprofiler import notifier


# NOTE(boris-42): Thread safe storage for profiler instances.
__local_ctx = threading.local()


def _clean():
    __local_ctx.profiler = None


def init(base_id=None, parent_id=None, hmac_key=None):
    """Init profiler.
    :param base_id: Used to bind all related traces.
    :param parent_id: Used to build tree of traces.
    :returns: Profiler instance
    """
    __local_ctx.profiler = Profiler(base_id=base_id, parent_id=parent_id,
                                    hmac_key=hmac_key)
    return __local_ctx.profiler


def get_profiler():
    """Get profiler instance.

    :returns: Profiler instance or None if profiler wasn't inited.
    """
    return getattr(__local_ctx, "profiler", None)


def start(name, info=None):
    """Send new start notification if profiler instance is presented."""
    profiler = get_profiler()
    if profiler:
        profiler.start(name, info=info)


def stop(info=None):
    """Send new stop notification if profiler instance is presented."""
    profiler = get_profiler()
    if profiler:
        profiler.stop(info=info)


class Profiler(object):

    def __init__(self, base_id=None, parent_id=None, hmac_key=None):
        self.notifier = notifier.get_notifier()
        self.hmac_key = hmac_key
        if not base_id:
            base_id = str(uuid.uuid4())
        self._trace_stack = collections.deque([base_id, parent_id or base_id])
        self._name = collections.deque()

    def __call__(self, name, info=None):
        """This method simplifies usage of profiler object as a guard
        > profiler = Profiler(service='nova')
        > with profiler('some long running code'):
        >     do_some_stuff()
        """
        self._name.append(name)
        self._info = info
        return self

    def __enter__(self):
        self.start(self._name[-1], info=self._info)

    def __exit__(self, etype, value, traceback):
        self.stop()

    def get_base_id(self):
        return self._trace_stack[0]

    def get_parent_id(self):
        return self._trace_stack[-2]

    def get_id(self):
        return self._trace_stack[-1]

    def start(self, name, info=None):
        """Currently time measurement itself is delegated to
        notification.api. Every message is marked with a unix
        timestamp and for now it should be sufficient.
        Later more precise measurements can be added here.
        """
        self._name.append(name)
        self._trace_stack.append(str(uuid.uuid4()))
        self._notify('%s-start' % name, info)

    def stop(self, info=None):
        self._notify('%s-stop' % self._name.pop(), info)
        self._trace_stack.pop()

    def _notify(self, name, info):
        payload = {
            'name': name,
            'base_id': self.get_base_id(),
            'trace_id': self.get_id(),
            'parent_id': self.get_parent_id()
        }
        if info:
            payload['info'] = info

        self.notifier.notify(payload)
