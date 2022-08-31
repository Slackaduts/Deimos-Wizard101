# This file is for the created types that Deimos uses (or will use in the future)



class Orientation:
    def __init__(self, yaw: float, pitch: float, roll: float):
        self.yaw = yaw
        self.pitch = pitch
        self.roll = roll

    def __str__(self):
        return f"<Orientation ({self.yaw}, {self.pitch}, {self.roll})>"

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter((self.yaw, self.pitch, self.roll))


