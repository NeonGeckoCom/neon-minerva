# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2024 NeonGecko.com Inc.
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

import pytest

from os import environ
from port_for import get_port
from pytest_rabbitmq.factories.executor import RabbitMqExecutor
from pytest_rabbitmq.factories.process import get_config


@pytest.fixture(scope="class")
def rmq_instance(request, tmp_path_factory):
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

    # Init RMQ config
    rmq_username = environ.get("TEST_RMQ_USERNAME", "test_llm_user")
    rmq_password = environ.get("TEST_RMQ_PASSWORD", "test_llm_password")
    rmq_vhosts = environ.get("TEST_RMQ_VHOSTS", "/test")
    rabbit_executor.rabbitctl_output("add_user", rmq_username, rmq_password)
    for vhost in rmq_vhosts.split(","):
        rabbit_executor.rabbitctl_output("add_vhost", vhost)
        rabbit_executor.rabbitctl_output("set_permissions", "-p", vhost,
                                         rmq_username, ".*", ".*", ".*")
    request.cls.rmq_instance = rabbit_executor
