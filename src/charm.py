#!/usr/bin/env python3
# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

"""Charmed Operator for the OpenAirInterface 5G Core DU component."""


import logging

from charms.oai_5g_cu.v0.fiveg_f1 import FiveGF1Requires  # type: ignore[import]
from charms.observability_libs.v1.kubernetes_service_patch import (  # type: ignore[import]
    KubernetesServicePatch,
    ServicePort,
)
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase, ConfigChangedEvent, InstallEvent
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, WaitingStatus

from kubernetes import Kubernetes

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/opt/oai-gnb/etc"
CONFIG_FILE_NAME = "gnb.conf"


class Oai5GDUOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        """Observes juju events."""
        super().__init__(*args)
        self._container_name = self._service_name = "du"
        self._container = self.unit.get_container(self._container_name)
        self.service_patcher = KubernetesServicePatch(
            service_type="LoadBalancer",
            charm=self,
            ports=[
                ServicePort(
                    name="s1c",
                    port=int(self._config_gnb_s1c_port),
                    protocol="SCTP",
                    targetPort=int(self._config_gnb_s1c_port),
                ),
                ServicePort(
                    name="s1u",
                    port=int(self._config_gnb_s1u_port),
                    protocol="UDP",
                    targetPort=int(self._config_gnb_s1u_port),
                ),
                ServicePort(
                    name="x2c",
                    port=int(self._config_gnb_x2c_port),
                    protocol="UDP",
                    targetPort=int(self._config_gnb_x2c_port),
                ),
                ServicePort(
                    name="f1",
                    port=int(self._config_f1_du_port),
                    protocol="UDP",
                    targetPort=int(self._config_f1_du_port),
                ),
            ],
        )
        self.f1_requires = FiveGF1Requires(self, "fiveg-f1")
        self.kubernetes = Kubernetes(namespace=self.model.name)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.fiveg_f1_relation_changed, self._on_config_changed)

    def _on_install(self, event: InstallEvent) -> None:
        """Triggered on install event.

        Args:
            event: Juju event

        Returns:
            None
        """
        if not self.kubernetes.statefulset_is_patched(
            statefulset_name=self.app.name,
        ):
            self.kubernetes.patch_statefulset(
                statefulset_name=self.app.name,
            )

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Triggered on any change in configuration.

        Args:
            event: Config Changed Event

        Returns:
            None
        """
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for Pebble in workload container")
            event.defer()
            return
        if not self._f1_relation_created:
            self.unit.status = BlockedStatus("Waiting for relation to CU to be created")
            return
        if not self.f1_requires.cu_address_available:
            self.unit.status = WaitingStatus(
                "Waiting for CU IPv4 address to be available in relation data"
            )
            return
        self._push_config()
        self._update_pebble_layer()
        self.unit.status = ActiveStatus()

    def _update_pebble_layer(self) -> None:
        """Updates pebble layer with new configuration.

        Returns:
            None
        """
        self._container.add_layer("du", self._pebble_layer, combine=True)
        self._container.replan()
        self.unit.status = ActiveStatus()

    @property
    def _f1_relation_created(self) -> bool:
        return self._relation_created("fiveg-f1")

    def _relation_created(self, relation_name: str) -> bool:
        if not self.model.get_relation(relation_name):
            return False
        return True

    def _push_config(self) -> None:
        jinja2_environment = Environment(loader=FileSystemLoader("src/templates/"))
        template = jinja2_environment.get_template(f"{CONFIG_FILE_NAME}.j2")
        content = template.render(
            gnb_du_name=self._config_gnb_du_name,
            gnb_du_id=self._config_gnb_du_id,
            tac=self._config_tac,
            mcc=self._config_mcc,
            mnc=self._config_mnc,
            mnc_length=self._config_mnc_length,
            nssai_sst=self._config_nssai_sst,
            nssai_sd=self._config_nssai_sd,
            du_f1_interface_name=self._config_du_f1_interface_name,
            du_f1_ipv4_address=self._du_ip_address,
            cu_f1_ipv4_address=self.f1_requires.cu_address,
            du_f1_port=self._config_f1_du_port,
            cu_f1_port=self.f1_requires.cu_port,
            thread_parallel_config=self._config_thread_parallel_config,
        )

        self._container.push(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}", source=content)
        logger.info(f"Wrote file to container: {CONFIG_FILE_NAME}")

    @property
    def _config_file_is_pushed(self) -> bool:
        """Check if config file is pushed to the container."""
        if not self._container.exists(f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"):
            logger.info(f"Config file is not written: {CONFIG_FILE_NAME}")
            return False
        logger.info("Config file is pushed")
        return True

    @property
    def _config_gnb_du_name(self) -> str:
        return "oai-du-rfsim"

    @property
    def _config_gnb_du_id(self) -> str:
        return "e00"

    @property
    def _config_tac(self) -> str:
        return "1"

    @property
    def _config_mcc(self) -> str:
        return self.model.config["mcc"]

    @property
    def _config_mnc(self) -> str:
        return self.model.config["mnc"]

    @property
    def _config_mnc_length(self) -> str:
        return self.model.config["mnc-length"]

    @property
    def _config_nssai_sst(self) -> str:
        return self.model.config["nssai-sst"]

    @property
    def _config_nssai_sd(self) -> str:
        return self.model.config["nssai-sd"]

    @property
    def _config_du_f1_interface_name(self) -> str:
        return "eth0"

    @property
    def _config_gnb_s1c_port(self) -> str:
        return "36412"

    @property
    def _config_gnb_s1u_port(self) -> str:
        return "2152"

    @property
    def _config_gnb_x2c_port(self) -> str:
        return "36422"

    @property
    def _config_f1_du_port(self) -> str:
        return "2153"

    @property
    def _config_thread_parallel_config(self) -> str:
        return "PARALLEL_SINGLE_THREAD"

    @property
    def _du_ip_address(self) -> str:
        du_hostname, du_ipv4_address = self.kubernetes.get_service_load_balancer_address(
            name=self.app.name
        )
        if not du_ipv4_address:
            raise ValueError("No IPv4 address found for DU")
        return du_ipv4_address

    @property
    def _pebble_layer(self) -> dict:
        """Return a dictionary representing a Pebble layer."""
        return {
            "summary": "du layer",
            "description": "pebble config layer for du",
            "services": {
                self._service_name: {
                    "override": "replace",
                    "summary": "du",
                    "command": f"/opt/oai-gnb/bin/nr-softmodem -O {BASE_CONFIG_PATH}/{CONFIG_FILE_NAME} --sa -E --rfsim --log_config.global_log_options level nocolor time",  # noqa: E501
                    "startup": "enabled",
                }
            },
        }


if __name__ == "__main__":
    main(Oai5GDUOperatorCharm)
