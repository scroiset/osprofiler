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

from osprofiler import profiler


def before_execute(name):
    """Add listener that will send trace info before query is executed."""

    def handler(conn, clauseelement, multiparams, params):
        info = {"db.statement": str(clauseelement),
                "db.multiparams": str(multiparams),
                "db.params": str(params)}
        profiler.start(name, info=info)

    return handler


def after_execute():
    """Add listener that will send trace info after query is executed."""

    def handler(conn, clauseelement, multiparams, params, result):
        profiler.stop(info=None)

    return handler


_DISABLED = False


def disable():
    global _DISABLED
    _DISABLED = True


def enable():
    global _DISABLED
    _DISABLED = False


def add_tracing(sqlalchemy, engine, name):
    """Add tracing to all sqlalchemy calls."""

    if not _DISABLED:
        sqlalchemy.event.listen(engine, 'before_execute', before_execute(name))
        sqlalchemy.event.listen(engine, 'after_execute', after_execute())
