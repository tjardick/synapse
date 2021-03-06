# -*- coding: utf-8 -*-
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


from tests import unittest
from twisted.internet import defer

from synapse.server import HomeServer
from synapse.api.events.room import (
    RoomNameEvent, RoomTopicEvent
)

from tests.utils import SQLiteMemoryDbPool


class RoomStoreTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        db_pool = SQLiteMemoryDbPool()
        yield db_pool.prepare()

        hs = HomeServer("test",
            db_pool=db_pool,
        )

        # We can't test RoomStore on its own without the DirectoryStore, for
        # management of the 'room_aliases' table
        self.store = hs.get_datastore()

        self.room = hs.parse_roomid("!abcde:test")
        self.alias = hs.parse_roomalias("#a-room-name:test")
        self.u_creator = hs.parse_userid("@creator:test")

        yield self.store.store_room(self.room.to_string(),
            room_creator_user_id=self.u_creator.to_string(),
            is_public=True
        )

    @defer.inlineCallbacks
    def test_get_room(self):
        self.assertObjectHasAttributes(
            {"room_id": self.room.to_string(),
             "creator": self.u_creator.to_string(),
             "is_public": True},
            (yield self.store.get_room(self.room.to_string()))
        )

    @defer.inlineCallbacks
    def test_store_room_config(self):
        yield self.store.store_room_config(self.room.to_string(),
            visibility=False
        )

        self.assertObjectHasAttributes(
            {"is_public": False},
            (yield self.store.get_room(self.room.to_string()))
        )

    @defer.inlineCallbacks
    def test_get_rooms(self):
        # get_rooms does an INNER JOIN on the room_aliases table :(

        rooms = yield self.store.get_rooms(is_public=True)
        # Should be empty before we add the alias
        self.assertEquals([], rooms)

        yield self.store.create_room_alias_association(
            room_alias=self.alias,
            room_id=self.room.to_string(),
            servers=["test"]
        )

        rooms = yield self.store.get_rooms(is_public=True)

        self.assertEquals(1, len(rooms))
        self.assertEquals({
            "name": None,
            "room_id": self.room.to_string(),
            "topic": None,
            "aliases": [self.alias.to_string()],
        }, rooms[0])


class RoomEventsStoreTestCase(unittest.TestCase):

    @defer.inlineCallbacks
    def setUp(self):
        db_pool = SQLiteMemoryDbPool()
        yield db_pool.prepare()

        hs = HomeServer("test",
            db_pool=db_pool,
        )

        # Room events need the full datastore, for persist_event() and
        # get_room_state()
        self.store = hs.get_datastore()
        self.event_factory = hs.get_event_factory();

        self.room = hs.parse_roomid("!abcde:test")

        yield self.store.store_room(self.room.to_string(),
            room_creator_user_id="@creator:text",
            is_public=True
        )

    @defer.inlineCallbacks
    def inject_room_event(self, **kwargs):
        yield self.store.persist_event(
            self.event_factory.create_event(
                room_id=self.room.to_string(),
                **kwargs
            )
        )

    @defer.inlineCallbacks
    def STALE_test_room_name(self):
        name = u"A-Room-Name"

        yield self.inject_room_event(
            etype=RoomNameEvent.TYPE,
            name=name,
            content={"name": name},
            depth=1,
        )

        state = yield self.store.get_current_state(
            room_id=self.room.to_string()
        )

        self.assertEquals(1, len(state))
        self.assertObjectHasAttributes(
            {"type": "m.room.name",
             "room_id": self.room.to_string(),
             "name": name},
            state[0]
        )

    @defer.inlineCallbacks
    def STALE_test_room_topic(self):
        topic = u"A place for things"

        yield self.inject_room_event(
            etype=RoomTopicEvent.TYPE,
            topic=topic,
            content={"topic": topic},
            depth=1,
        )

        state = yield self.store.get_current_state(
            room_id=self.room.to_string()
        )

        self.assertEquals(1, len(state))
        self.assertObjectHasAttributes(
            {"type": "m.room.topic",
             "room_id": self.room.to_string(),
             "topic": topic},
            state[0]
        )

    # Not testing the various 'level' methods for now because there's lots
    # of them and need coalescing; see JIRA SPEC-11
