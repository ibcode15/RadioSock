from dataclasses import dataclass


class SongInfo:
	def __init__(
		self,
		name: str,
		format_from_width: str = None,
		channels: int = None,
		rate: int = None
		):
		self.name = name
		self.format = format_from_width
		self.channels = channels
		self.rate = rate
class SongPacket:
	def __init__(self, data: bytes):
		self.data = data