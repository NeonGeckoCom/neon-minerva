# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2025 NeonGecko.com Inc.
# BSD-3
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import atexit
import os
import signal
import sys
import threading
import time

import pytest

from os import environ
from port_for import get_port
from pytest_rabbitmq.factories.executor import RabbitMqExecutor
from pytest_rabbitmq.factories.process import get_config


# Track every executor we hand out so that interpreter shutdown can stop
# any that test code or another fixture forgot to release.
_ACTIVE_RMQ_EXECUTORS: "list[RabbitMqExecutor]" = []

# Maximum time we'll spend trying to gracefully stop a single
# ``RabbitMqExecutor`` before falling back to a direct SIGKILL of its
# process group.
_RMQ_STOP_TIMEOUT_SECONDS = 10

# How long, after the test session reaches teardown / interpreter shutdown,
# we'll let the rest of the cleanup run before forcefully exiting. The
# Erlang VM that backs RabbitMQ has been observed to ignore the signal
# sent by ``mirakuru``'s ``stop`` / ``__del__`` / ``atexit`` cleanup on
# GitHub-hosted runners, leaving pytest blocked after it has already
# reported its results. The watchdog runs in a daemon thread so it can
# never itself prevent exit.
_RMQ_FORCE_EXIT_GRACE_SECONDS = 30


def _kill_executor_processgroup(executor):
    """Send SIGKILL to the executor's process group, no questions asked.

    ``mirakuru`` sets ``os.setsid`` as ``preexec_fn`` for its subprocesses
    so the spawned process is its own group leader and ``killpg`` reaches
    every child the broker may have started. We deliberately avoid
    ``mirakuru.SimpleExecutor.stop`` / ``kill(wait=True)`` here because
    both call ``self.process.wait()`` which can block indefinitely if the
    subprocess refuses to die.
    """
    process = getattr(executor, "process", None)
    pid = getattr(process, "pid", None)
    if not pid:
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass


def _stop_executor_quietly(executor):
    """Best-effort, time-bounded teardown that never blocks indefinitely.

    First try ``executor.stop()`` in a daemon thread so we can give up if
    ``mirakuru`` blocks waiting for the broker to die. If that does not
    return inside ``_RMQ_STOP_TIMEOUT_SECONDS``, fall back to a direct
    ``killpg(SIGKILL)`` on the broker's process group and move on.
    """
    if executor is None:
        return

    stop_done = threading.Event()

    def _do_stop():
        try:
            if executor.running():
                executor.stop()
        except Exception:
            pass
        finally:
            stop_done.set()

    threading.Thread(
        target=_do_stop,
        name="neon-minerva-rmq-stop",
        daemon=True,
    ).start()

    if not stop_done.wait(_RMQ_STOP_TIMEOUT_SECONDS):
        _kill_executor_processgroup(executor)


def _force_exit_on_stalled_shutdown():
    """Last-resort safety net for interpreter shutdown.

    Stops any executors we still know about (in case a test or downstream
    fixture leaked one) and arms a daemon-thread watchdog that ``os._exit``s
    if the rest of the shutdown sequence does not complete in
    ``_RMQ_FORCE_EXIT_GRACE_SECONDS`` seconds. The watchdog spawns and the
    hook returns immediately so other ``atexit`` hooks (notably
    ``mirakuru.base.cleanup_subprocesses``) still get to run.
    """
    for executor in list(_ACTIVE_RMQ_EXECUTORS):
        _stop_executor_quietly(executor)
    _ACTIVE_RMQ_EXECUTORS.clear()
    _arm_force_exit_watchdog(_RMQ_FORCE_EXIT_GRACE_SECONDS, exit_code=0)


def _arm_force_exit_watchdog(grace_seconds, exit_code=0):
    """Spawn a daemon thread that ``os._exit``s after ``grace_seconds``.

    Daemon threads are killed automatically when the main thread exits, so
    on a healthy shutdown the watchdog never fires. It only matters when
    the surrounding teardown code stalls -- in which case the watchdog
    forcibly terminates the process so the surrounding job (CI step, etc.)
    can move on instead of silently deadlocking.
    """
    def _watchdog():
        time.sleep(grace_seconds)
        sys.stderr.write(
            f"\n[neon_minerva.rabbit_mq] forcing process exit after "
            f"{grace_seconds}s grace period; shutdown stalled.\n"
        )
        sys.stderr.flush()
        os._exit(exit_code)

    threading.Thread(
        target=_watchdog,
        name="neon-minerva-rmq-force-exit",
        daemon=True,
    ).start()


# Register at import time so the hook is always armed when the fixture is
# in use, regardless of whether ``neon-minerva`` is loaded as a pytest
# plugin via entry points or simply imported by a test module.
atexit.register(_force_exit_on_stalled_shutdown)


@pytest.fixture(scope="class")
def rmq_instance(request, tmp_path_factory):
    """Start a RabbitMQ subprocess for the test class and stop it after.

    The fixture used to leak the broker subprocess and rely solely on
    ``mirakuru``'s ``atexit`` cleanup. That cleanup is unreliable in CI
    (notably on GitHub Actions) because the Erlang VM backing RabbitMQ does
    not always die when the wrapper process is signalled at interpreter
    shutdown, which leaves ``pytest`` hung after every test has reported as
    ``PASSED``. We now perform an explicit teardown via ``yield``/``finally``
    so the broker is stopped as soon as the test class is done with it.
    """
    config = get_config(request)
    rabbit_ctl = config["ctl"]
    rabbit_server = config["server"]
    rabbit_host = "127.0.0.1"
    rabbit_port = get_port(config["port"])
    rabbit_distribution_port = get_port(
        config["distribution_port"], [rabbit_port]
    )
    assert rabbit_distribution_port
    assert (
            rabbit_distribution_port != rabbit_port
    ), "rabbit_port and distribution_port can not be the same!"

    tmpdir = tmp_path_factory.mktemp(f"pytest-rabbitmq-{request.fixturename}")

    rabbit_plugin_path = config["plugindir"]

    rabbit_logpath = config["logsdir"]

    if not rabbit_logpath:
        rabbit_logpath = tmpdir / "logs"

    rabbit_executor = RabbitMqExecutor(
        rabbit_server,
        rabbit_host,
        rabbit_port,
        rabbit_distribution_port,
        rabbit_ctl,
        logpath=rabbit_logpath,
        path=tmpdir,
        plugin_path=rabbit_plugin_path,
        node_name=config["node"],
    )

    rabbit_executor.start()
    _ACTIVE_RMQ_EXECUTORS.append(rabbit_executor)

    # Init RMQ config
    rmq_username = environ.get("TEST_RMQ_USERNAME", "test_user")
    rmq_password = environ.get("TEST_RMQ_PASSWORD", "test_password")
    rmq_vhosts = environ.get("TEST_RMQ_VHOSTS", "/test")
    rabbit_executor.rabbitctl_output("add_user", rmq_username, rmq_password)
    for vhost in rmq_vhosts.split(","):
        rabbit_executor.rabbitctl_output("add_vhost", vhost)
        rabbit_executor.rabbitctl_output("set_permissions", "-p", vhost,
                                         rmq_username, ".*", ".*", ".*")
    request.cls.rmq_instance = rabbit_executor
    try:
        yield rabbit_executor
    finally:
        _stop_executor_quietly(rabbit_executor)
        try:
            _ACTIVE_RMQ_EXECUTORS.remove(rabbit_executor)
        except ValueError:
            pass
