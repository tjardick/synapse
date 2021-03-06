# Copyright 2014 OpenMarket Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from twisted.internet import defer
from tests import unittest

from synapse.api.events.room import (
    MessageEvent,
)

from synapse.api.events import SynapseEvent
from synapse.handlers.federation import FederationHandler
from synapse.server import HomeServer

from mock import NonCallableMock, ANY, Mock

from ..utils import MockKey


class FederationTestCase(unittest.TestCase):

    def setUp(self):

        self.mock_config = NonCallableMock()
        self.mock_config.signing_key = [MockKey()]

        self.state_handler = NonCallableMock(spec_set=[
            "annotate_event_with_state",
        ])

        self.auth = NonCallableMock(spec_set=[
            "check",
            "check_host_in_room",
        ])

        self.hostname = "test"
        hs = HomeServer(
            self.hostname,
            db_pool=None,
            datastore=NonCallableMock(spec_set=[
                "persist_event",
                "store_room",
                "get_room",
            ]),
            resource_for_federation=NonCallableMock(),
            http_client=NonCallableMock(spec_set=[]),
            notifier=NonCallableMock(spec_set=["on_new_room_event"]),
            handlers=NonCallableMock(spec_set=[
                "room_member_handler",
                "federation_handler",
            ]),
            config=self.mock_config,
            auth=self.auth,
            state_handler=self.state_handler,
            keyring=Mock(),
        )

        self.datastore = hs.get_datastore()
        self.handlers = hs.get_handlers()
        self.notifier = hs.get_notifier()
        self.hs = hs

        self.handlers.federation_handler = FederationHandler(self.hs)

    @defer.inlineCallbacks
    def test_msg(self):
        pdu = SynapseEvent(
            type=MessageEvent.TYPE,
            room_id="foo",
            content={"msgtype": u"fooo"},
            origin_server_ts=0,
            event_id="$a:b",
            user_id="@a:b",
            origin="b",
            auth_events=[],
            hashes={"sha256":"AcLrgtUIqqwaGoHhrEvYG1YLDIsVPYJdSRGhkp3jJp8"},
        )

        self.datastore.persist_event.return_value = defer.succeed(None)
        self.datastore.get_room.return_value = defer.succeed(True)
        self.auth.check_host_in_room.return_value = defer.succeed(True)

        def annotate(ev, old_state=None):
            ev.old_state_events = []
            return defer.succeed(False)
        self.state_handler.annotate_event_with_state.side_effect = annotate

        yield self.handlers.federation_handler.on_receive_pdu(
            "fo", pdu, False
        )

        self.datastore.persist_event.assert_called_once_with(
            ANY, is_new_state=False, backfilled=False, current_state=None
        )

        self.state_handler.annotate_event_with_state.assert_called_once_with(
            ANY,
            old_state=None,
        )

        self.auth.check.assert_called_once_with(ANY, auth_events={})

        self.notifier.on_new_room_event.assert_called_once_with(
            ANY,
            extra_users=[]
        )
