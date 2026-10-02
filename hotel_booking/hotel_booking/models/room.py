"""Room model."""
from utils.constants import ROOM_STATUS_AVAILABLE


class Room:
    def __init__(self, room_id, room_number, room_type, price_per_night,
                 capacity, floor, status=ROOM_STATUS_AVAILABLE,
                 description=""):
        self.room_id = room_id
        self.room_number = room_number
        self.room_type = room_type
        self.price_per_night = price_per_night
        self.capacity = capacity
        self.floor = floor
        self.status = status
        self.description = description

    @property
    def is_available(self):
        return self.status == ROOM_STATUS_AVAILABLE

    def can_host(self, guests):
        return guests <= self.capacity

    def to_dict(self):
        return {
            "room_id": self.room_id,
            "room_number": self.room_number,
            "room_type": self.room_type,
            "price_per_night": self.price_per_night,
            "capacity": self.capacity,
            "floor": self.floor,
            "status": self.status,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            room_id=int(data["room_id"]),
            room_number=str(data["room_number"]),
            room_type=str(data["room_type"]),
            price_per_night=float(data["price_per_night"]),
            capacity=int(data["capacity"]),
            floor=int(data["floor"]),
            status=str(data.get("status", ROOM_STATUS_AVAILABLE)),
            description=str(data.get("description", "")),
        )
