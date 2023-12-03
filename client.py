import socket
from time import sleep
import pickle
import RadioTypes
import codecs
from threading import Thread
import pyaudio
import queue


class Client:
	def __init__(self, ip: str, port: int):
		self.ip = ip
		self.port = port
		self.music_queue = queue.Queue()
		self.running = True
		self.threads = {}
		self.sock = None
		self.audio_obj = pyaudio.PyAudio()
		self.current_song_obj = None



	def run(self):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.connect((self.ip, self.port))
			print("connected to server")
			self.sock = s
			self.threads["MusicReceiver"] = Thread(target = self.music_receiver_thread)
			self.threads["MusicStreamer"] = Thread(target = self.music_streamer_thread)
			for (name, thread) in self.threads.items():
				thread.start()
				print(f"Starting thread: {name}")


			for (name, thread) in self.threads.items():
				thread.join()
				print(f"Ending thread: {name}")

	def music_receiver_thread(self):
		while self.running:
			data = self.recvall()
			datatype = type(data)
			if datatype == RadioTypes.SongInfo:
				self.current_song_obj = data

			elif datatype == RadioTypes.SongPacket:
				self.music_queue.put(data)
			else:
				print(f"Error: do not know this type {datatype}")

	def music_streamer_thread(self):
		current_song_obj_cache = self.current_song_obj
		stream = None
		chunk = 10*1024
		while self.running:
			while not self.music_queue.empty():
				if self.current_song_obj is not current_song_obj_cache:
					current_song_obj_cache = self.current_song_obj
					stream = self.audio_obj.open(
						format = current_song_obj_cache.format[0],
						channels = current_song_obj_cache.channels[0],
						rate = current_song_obj_cache.rate,
						output=True,
						frames_per_buffer=chunk
						)
					print(f"Now Playing {current_song_obj_cache.name}")
				music = self.music_queue.get()
				stream.write(music.data)
				self.music_queue.task_done()

	def recvall(self):
		size = 100000
		data = bytearray()
		while True:
			packet = self.sock.recv(size)
			if not packet:
				break
			data.extend(packet)
			try:
				return pickle.loads(bytes(data))
			except:
				pass
		return pickle.loads(bytes(data)) 
def main():
	ip = "192.168.0.82"
	port = 5000
	c = Client(ip, port)
	c.run()



if __name__ == "__main__":
	main()
