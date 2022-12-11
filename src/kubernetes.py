# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

"""Kubernetes specific utilities."""

import logging
from typing import Optional, Tuple

from lightkube import Client
from lightkube.resources.apps_v1 import StatefulSet
from lightkube.resources.core_v1 import Service
from lightkube.types import PatchType

logger = logging.getLogger(__name__)


class Kubernetes:
    """Kubernetes main class."""

    def __init__(self, namespace: str):
        """Initializes K8s client."""
        self.client = Client()
        self.namespace = namespace

    def get_service(self, name: str) -> Service:
        """Gets service based on name."""
        return self.client.get(Service, name, namespace=self.namespace)  # type: ignore[return-value]  # noqa: E501

    def get_service_load_balancer_address(self, name: str) -> Tuple[Optional[str], Optional[str]]:
        """Retrieves LoadBalancer address based on service name."""
        service = self.get_service(name)
        if service.spec.type != "LoadBalancer":
            raise RuntimeError("Service is not of type LoadBalancer.")
        ingress = service.status.loadBalancer.ingress
        if not ingress:
            raise RuntimeError("The service has no ingress address.")
        return ingress[0].hostname, ingress[0].ip

    def patch_statefulset(
        self,
        statefulset_name: str,
    ) -> None:
        """Patches a statefulset with volumes and volume mounts.

        Args:
            statefulset_name: Statefulset name.

        Returns:
            None
        """
        statefulset = self.client.get(
            res=StatefulSet, name=statefulset_name, namespace=self.namespace
        )
        if not hasattr(statefulset, "spec"):
            raise RuntimeError(f"Could not find `spec` in the {statefulset_name} statefulset")

        statefulset.spec.template.spec.securityContext.runAsUser = 0
        statefulset.spec.template.spec.securityContext.runAsGroup = 0
        statefulset.spec.template.spec.containers[1].securityContext.privileged = True

        self.client.patch(
            res=StatefulSet,
            name=statefulset_name,
            obj=statefulset,
            patch_type=PatchType.MERGE,
            namespace=self.namespace,
        )
        logger.info(f"Statefulset {statefulset_name} patched with security group")

    def statefulset_is_patched(self, statefulset_name: str) -> bool:
        """Returns whether the statefulset is patched or not.

        Args:
            statefulset_name: Statefulset name.

        Returns:
            True if the statefulset is patched, False otherwise.
        """
        statefulset = self.client.get(
            res=StatefulSet, name=statefulset_name, namespace=self.namespace
        )
        if not hasattr(statefulset, "spec"):
            raise RuntimeError(f"Could not find `spec` in the {statefulset_name} statefulset")

        if statefulset.spec.template.spec.securityContext.runAsUser != 0:
            logger.info("runAsUser is not set to 0")
            return False

        if statefulset.spec.template.spec.securityContext.runAsGroup != 0:
            logger.info("runAsGroup is not set to 0")
            return False

        if not statefulset.spec.template.spec.containers[1].securityContext.privileged:
            logger.info("workload container is not privileged")
            return False

        return True
