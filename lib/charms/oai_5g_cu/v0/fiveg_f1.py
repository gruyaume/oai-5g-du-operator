# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

"""Interface used by provider and requirer of the 5G F1."""

import logging
from typing import Optional

from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from ops.framework import EventBase, EventSource, Handle, Object


# The unique Charmhub library identifier, never change it
LIBID = "7951385bd79f4543840f5fc5aff1d1b1"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 2


logger = logging.getLogger(__name__)


class F1AvailableEvent(EventBase):
    """Charm event emitted when an F1 is available."""

    def __init__(
        self,
        handle: Handle,
        cu_address: str,
        cu_port: str,
    ):
        """Init."""
        super().__init__(handle)
        self.cu_address = cu_address
        self.cu_port = cu_port

    def snapshot(self) -> dict:
        """Returns snapshot."""
        return {
            "cu_address": self.cu_address,
            "cu_port": self.cu_port,
        }

    def restore(self, snapshot: dict) -> None:
        """Restores snapshot."""
        self.cu_address = snapshot["cu_address"]
        self.cu_port = snapshot["cu_port"]


class FiveGF1RequirerCharmEvents(CharmEvents):
    """List of events that the 5G F1 requirer charm can leverage."""

    cu_available = EventSource(F1AvailableEvent)


class FiveGF1Requires(Object):
    """Class to be instantiated by the charm requiring the 5G F1 Interface."""

    on = FiveGF1RequirerCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str):
        """Init."""
        super().__init__(charm, relationship_name)
        self.charm = charm
        self.relationship_name = relationship_name
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_relation_changed
        )

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Handler triggered on relation changed event.

        Args:
            event: Juju event (RelationChangedEvent)

        Returns:
            None
        """
        relation = event.relation
        if not relation.app:
            logger.warning("No remote application in relation: %s", self.relationship_name)
            return
        remote_app_relation_data = relation.data[relation.app]
        if "cu_address" not in remote_app_relation_data:
            logger.info("No cu_address in relation data - Not triggering cu_available event")
            return
        if "cu_port" not in remote_app_relation_data:
            logger.info("No cu_port in relation data - Not triggering cu_available event")
            return
        self.on.cu_available.emit(
            cu_address=remote_app_relation_data["cu_address"],
            cu_port=remote_app_relation_data["cu_port"],
        )

    @property
    def cu_address_available(self) -> bool:
        """Returns whether cu address is available in relation data."""
        if self.cu_address:
            return True
        else:
            return False

    @property
    def cu_address(self) -> Optional[str]:
        """Returns cu_address from relation data."""
        relation = self.model.get_relation(relation_name=self.relationship_name)
        remote_app_relation_data = relation.data.get(relation.app)
        if not remote_app_relation_data:
            return None
        return remote_app_relation_data.get("cu_address", None)

    @property
    def cu_port_available(self) -> bool:
        """Returns whether cu port is available in relation data."""
        if self.cu_port:
            return True
        else:
            return False

    @property
    def cu_port(self) -> Optional[str]:
        """Returns cu_port from relation data."""
        relation = self.model.get_relation(relation_name=self.relationship_name)
        remote_app_relation_data = relation.data.get(relation.app)
        if not remote_app_relation_data:
            return None
        return remote_app_relation_data.get("cu_port", None)


class FiveGF1Provides(Object):
    """Class to be instantiated by the CU charm providing the 5G F1 Interface."""

    def __init__(self, charm: CharmBase, relationship_name: str):
        """Init."""
        super().__init__(charm, relationship_name)
        self.relationship_name = relationship_name
        self.charm = charm

    def set_cu_information(
        self,
        cu_address: str,
        cu_port: str,
        relation_id: int,
    ) -> None:
        """Sets F1 information in relation data.

        Args:
            cu_address: F1 CU address
            cu_port: F1 CU port
            relation_id: Relation ID

        Returns:
            None
        """
        relation = self.model.get_relation(self.relationship_name, relation_id=relation_id)
        if not relation:
            raise RuntimeError(f"Relation {self.relationship_name} not created yet.")
        relation.data[self.charm.app].update(
            {
                "cu_address": cu_address,
                "cu_port": cu_port,
            }
        )
