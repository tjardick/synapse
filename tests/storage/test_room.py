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
        room = yield self.store.get_room(self.room.to_string())

        self.assertEquals(self.room.to_string(), room.room_id)
        self.assertEquals(self.u_creator.to_string(), room.creator)
        self.assertTrue(room.is_public)

    @defer.inlineCallbacks
    def test_store_room_config(self):
        yield self.store.store_room_config(self.room.to_string(),
            visibility=False
        )

        room = yield self.store.get_room(self.room.to_string())

        self.assertFalse(room.is_public)

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