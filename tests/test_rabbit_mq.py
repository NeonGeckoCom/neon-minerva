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

import os
import signal
import time
from unittest.mock import MagicMock, patch

import pytest

from neon_minerva.integration import rabbit_mq


@pytest.fixture(autouse=True)
def _clear_tracked_executors():
    """Keep executor tracking list isolated across tests."""
    rabbit_mq._ACTIVE_RMQ_EXECUTORS.clear()
    yield
    rabbit_mq._ACTIVE_RMQ_EXECUTORS.clear()


class TestKillExecutorProcessgroup:
    def test_no_process_is_noop(self):
        executor = MagicMock(spec=[])
        rabbit_mq._kill_executor_processgroup(executor)

    def test_no_pid_is_noop(self):
        executor = MagicMock()
        executor.process = MagicMock()
        executor.process.pid = None
        with patch.object(rabbit_mq.os, "killpg") as killpg:
            rabbit_mq._kill_executor_processgroup(executor)
        killpg.assert_not_called()

    def test_sends_sigkill_to_process_group(self):
        executor = MagicMock()
        executor.process.pid = 4242
        with patch.object(rabbit_mq.os, "killpg") as killpg:
            rabbit_mq._kill_executor_processgroup(executor)
        killpg.assert_called_once_with(4242, signal.SIGKILL)

    def test_oserror_is_swallowed(self):
        executor = MagicMock()
        executor.process.pid = 4242
        with patch.object(rabbit_mq.os, "killpg", side_effect=OSError):
            rabbit_mq._kill_executor_processgroup(executor)

    def test_process_lookup_error_is_swallowed(self):
        executor = MagicMock()
        executor.process.pid = 4242
        with patch.object(rabbit_mq.os, "killpg",
                          side_effect=ProcessLookupError):
            rabbit_mq._kill_executor_processgroup(executor)


class TestStopExecutorQuietly:
    def test_none_executor_is_noop(self):
        rabbit_mq._stop_executor_quietly(None)

    def test_stop_called_when_running(self):
        executor = MagicMock()
        executor.running.return_value = True
        with patch.object(rabbit_mq, "_RMQ_STOP_TIMEOUT_SECONDS", 2):
            rabbit_mq._stop_executor_quietly(executor)
        executor.stop.assert_called_once_with()

    def test_stop_skipped_when_not_running(self):
        executor = MagicMock()
        executor.running.return_value = False
        with patch.object(rabbit_mq, "_RMQ_STOP_TIMEOUT_SECONDS", 2):
            rabbit_mq._stop_executor_quietly(executor)
        executor.stop.assert_not_called()

    def test_stop_exception_is_swallowed(self):
        executor = MagicMock()
        executor.running.return_value = True
        executor.stop.side_effect = RuntimeError("boom")
        with patch.object(rabbit_mq, "_RMQ_STOP_TIMEOUT_SECONDS", 2):
            rabbit_mq._stop_executor_quietly(executor)

    def test_timeout_falls_back_to_killpg(self):
        executor = MagicMock()
        executor.running.return_value = True

        def _hang_stop():
            time.sleep(1.0)

        executor.stop.side_effect = _hang_stop
        with patch.object(rabbit_mq, "_RMQ_STOP_TIMEOUT_SECONDS", 0.05), \
                patch.object(rabbit_mq, "_kill_executor_processgroup") as kill:
            rabbit_mq._stop_executor_quietly(executor)
        kill.assert_called_once_with(executor)


class TestStopAllTrackedExecutors:
    def test_stops_and_clears_tracked_executors(self):
        first = MagicMock(name="first")
        second = MagicMock(name="second")
        rabbit_mq._ACTIVE_RMQ_EXECUTORS.extend([first, second])
        with patch.object(rabbit_mq, "_stop_executor_quietly") as stop:
            rabbit_mq._stop_all_tracked_executors()
        assert stop.call_count == 2
        stop.assert_any_call(first)
        stop.assert_any_call(second)
        assert rabbit_mq._ACTIVE_RMQ_EXECUTORS == []


class TestArmForceExitWatchdog:
    def test_spawns_daemon_watchdog_that_exits(self):
        with patch.object(rabbit_mq.time, "sleep") as sleep, \
                patch.object(rabbit_mq.os, "_exit") as force_exit, \
                patch.object(rabbit_mq.sys.stderr, "write"), \
                patch.object(rabbit_mq.sys.stderr, "flush"):
            rabbit_mq._arm_force_exit_watchdog(0.01, exit_code=7)
            # Allow daemon thread to run
            deadline = time.time() + 2
            while not force_exit.called and time.time() < deadline:
                time.sleep(0.01)
        sleep.assert_called_once_with(0.01)
        force_exit.assert_called_once_with(7)


class TestForceExitOnStalledShutdown:
    def test_stops_tracked_and_arms_watchdog(self):
        with patch.object(rabbit_mq, "_stop_all_tracked_executors") as stop, \
                patch.object(rabbit_mq, "_arm_force_exit_watchdog") as arm:
            rabbit_mq._force_exit_on_stalled_shutdown()
        stop.assert_called_once_with()
        arm.assert_called_once_with(
            rabbit_mq._RMQ_FORCE_EXIT_GRACE_SECONDS, exit_code=0
        )


class TestPytestSessionfinish:
    def test_stops_tracked_and_arms_watchdog_with_exit_status(self):
        session = MagicMock()
        with patch.object(rabbit_mq, "_stop_all_tracked_executors") as stop, \
                patch.object(rabbit_mq, "_arm_force_exit_watchdog") as arm:
            rabbit_mq.pytest_sessionfinish(session, exitstatus=3)
        stop.assert_called_once_with()
        arm.assert_called_once_with(
            rabbit_mq._RMQ_FORCE_EXIT_GRACE_SECONDS, exit_code=3
        )

    def test_non_int_exitstatus_defaults_to_zero(self):
        session = MagicMock()
        with patch.object(rabbit_mq, "_stop_all_tracked_executors"), \
                patch.object(rabbit_mq, "_arm_force_exit_watchdog") as arm:
            rabbit_mq.pytest_sessionfinish(session, exitstatus="failed")
        arm.assert_called_once_with(
            rabbit_mq._RMQ_FORCE_EXIT_GRACE_SECONDS, exit_code=0
        )


def _rmq_instance_impl():
    """Underlying fixture function (pytest forbids calling fixtures directly)."""
    return rabbit_mq.rmq_instance._get_wrapped_function()


class TestRmqInstanceMissingExtras:
    def test_raises_when_optional_deps_missing(self):
        request = MagicMock()
        tmp_path_factory = MagicMock()
        with patch.object(rabbit_mq, "_INITIALIZED", False):
            with pytest.raises(ModuleNotFoundError, match="neon-minerva\\[rmq\\]"):
                next(_rmq_instance_impl()(request, tmp_path_factory))


class TestRmqInstanceFixtureUnit:
    def test_starts_configures_and_tracks_executor(self, tmp_path_factory):
        request = MagicMock()
        request.fixturename = "rmq_instance"
        request.cls = type("Dummy", (), {})()

        executor = MagicMock()
        executor.running.return_value = True
        config = {
            "ctl": "/usr/lib/rabbitmq/bin/rabbitmqctl",
            "server": "/usr/lib/rabbitmq/bin/rabbitmq-server",
            "port": None,
            "distribution_port": None,
            "plugindir": tmp_path_factory.mktemp("plugins"),
            "logsdir": None,
            "node": "rabbit@localhost",
        }

        with patch.object(rabbit_mq, "_INITIALIZED", True), \
                patch.object(rabbit_mq, "get_config", return_value=config), \
                patch.object(rabbit_mq, "get_port", side_effect=[5672, 25672]), \
                patch.object(rabbit_mq, "RabbitMqExecutor",
                             return_value=executor) as executor_cls, \
                patch.dict(os.environ, {
                    "TEST_RMQ_USERNAME": "ci_user",
                    "TEST_RMQ_PASSWORD": "ci_pass",
                    "TEST_RMQ_VHOSTS": "/a,/b",
                }, clear=False), \
                patch.object(rabbit_mq, "_stop_executor_quietly") as stop:
            gen = _rmq_instance_impl()(request, tmp_path_factory)
            yielded = next(gen)
            assert yielded is executor
            assert request.cls.rmq_instance is executor
            assert executor in rabbit_mq._ACTIVE_RMQ_EXECUTORS
            executor.start.assert_called_once_with()
            executor.rabbitctl_output.assert_any_call(
                "add_user", "ci_user", "ci_pass"
            )
            executor.rabbitctl_output.assert_any_call("add_vhost", "/a")
            executor.rabbitctl_output.assert_any_call("add_vhost", "/b")
            executor.rabbitctl_output.assert_any_call(
                "set_permissions", "-p", "/a", "ci_user", ".*", ".*", ".*"
            )
            executor.rabbitctl_output.assert_any_call(
                "set_permissions", "-p", "/b", "ci_user", ".*", ".*", ".*"
            )
            executor_cls.assert_called_once()

            with pytest.raises(StopIteration):
                next(gen)

            stop.assert_called_once_with(executor)
            assert executor not in rabbit_mq._ACTIVE_RMQ_EXECUTORS

    def test_rejects_identical_ports(self, tmp_path_factory):
        request = MagicMock()
        request.fixturename = "rmq_instance"
        config = {
            "ctl": "ctl",
            "server": "server",
            "port": None,
            "distribution_port": None,
            "plugindir": tmp_path_factory.mktemp("plugins"),
            "logsdir": None,
            "node": "rabbit@localhost",
        }
        with patch.object(rabbit_mq, "_INITIALIZED", True), \
                patch.object(rabbit_mq, "get_config", return_value=config), \
                patch.object(rabbit_mq, "get_port", side_effect=[5672, 5672]):
            with pytest.raises(AssertionError, match="can not be the same"):
                next(_rmq_instance_impl()(request, tmp_path_factory))


@pytest.mark.usefixtures("rmq_instance")
class TestRmqInstanceIntegration:
    """Live RabbitMQ subprocess smoke test for the class-scoped fixture."""

    def test_broker_is_running_with_configured_user(self):
        assert self.rmq_instance.running()
        assert self.rmq_instance.port
        # Default fixture credentials from rabbit_mq.py
        users = self.rmq_instance.rabbitctl_output("list_users")
        assert "test_user" in users
        vhosts = self.rmq_instance.rabbitctl_output("list_vhosts")
        assert "/test" in vhosts
