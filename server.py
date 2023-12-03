import socket
import glob
import random
import wave
import pickle
import codecs
from threading import Thread
from multiprocessing import Process,JoinableQueue
import types
from time import sleep
from dataclasses import dataclass
import os
import pyaudio
import RadioTypes
import struct

@dataclass
class Client:
	sock: socket.socket
	ip: str
	port: int



class RadioStation(Process):
	def __init__(self, name: str, songlist: list[str], port: int, ip: str):
		Process.__init__(self)

		self.name = name
		self.songs = songlist
		self.songs_len = len(self.songs)
		self.pointer = 0
		
		self.data = b''
		self.data_flag = False

		self.running = True
		self.ip = ip
		self.port = port
		self.audio_chunk = 10*1024
		self.threads = {}
		self.clients: dict[tuple,Client] = {}

		self.PacketQueue = JoinableQueue()

		self.current_song_info = None
	def run(self):
		self.threads["server"] = Thread(target = self.server_thread)
		self.threads["Dj"] = Thread(target = self.Dj_thread)
		self.threads["PacketSender"] = Thread(target = self.packet_sender_thread)
		for (name, thread) in self.threads.items():
			thread.start()
			self.log(name, "Starting thread")
		


		for (name, thread) in self.threads.items():
			thread.join()
			self.log(name, "closing thread")
	def AudioStream(self, file: str):
		file_name = os.path.splitext(os.path.basename(file))[0]
		SongInfoPacket = RadioTypes.SongInfo(name = file_name)
		p = pyaudio.PyAudio()

		with wave.open(file,"rb") as f:
			SongInfoPacket.format = p.get_format_from_width(f.getsampwidth()),
			SongInfoPacket.channels = f.getnchannels(),
			SongInfoPacket.rate = f.getframerate()
			self.current_song_info = SongInfoPacket
			self.PacketQueue.put((SongInfoPacket,True))
			stream = p.open(
				format = SongInfoPacket.format[0],
				channels = SongInfoPacket.channels[0],  
                rate = SongInfoPacket.rate,  
                output = True
                )
			data = f.readframes(self.audio_chunk)
			print(0.97*self.audio_chunk/SongInfoPacket.rate)
			while len(data) > 0:
				data = f.readframes(self.audio_chunk)
				self.PacketQueue.put((RadioTypes.SongPacket(data = data),True))
				#sleep(0.217)
				sleep(0.97*self.audio_chunk/SongInfoPacket.rate)

	def packet_sender_thread(self):
		while self.running:
			while not self.PacketQueue.empty():
				value = self.PacketQueue.get()
				if type(value) != tuple:
					self.log("PacketSender", "Value in queue is not a tuple")
					exit(1)
				packet, clients = value
				packet_type = type(packet).__name__
				if type(packet) != bytes:
					packet = pickle.dumps(packet)
				self.Broadcast(
					data = packet,
					type_of_data = packet_type,
					more_info = False,
					clients = clients
					)


				self.PacketQueue.task_done()


	def Broadcast(self, data: bytes, type_of_data: str, more_info: bool= False, clients: list | bool = True):

		if type(clients) != list and  type(clients) != bool:
			self.log("server", f"Error: incroect clients input on Broadcast: {clients}")
			return
		if type(clients) == bool:
			if clients == True:
				if more_info:
					self.log("server", f"Sending {type_of_data} packet to all the clients.")
				clients = self.clients.values()
			else:
				self.log("server", f"Error: incroect clients input on Broadcast: {clients}")
				return 
		else:
			if more_info:
				self.log("server", f"Sending {type_of_data} packet to some the clients.")

		disconnected_clients = []

		for client in clients:
			try:
				client.sock.sendall(data)
			except:
				self.log("server", f"Client has disconnected ({client.ip}:{client.port})")
				disconnected_clients.append(client)
		for c in disconnected_clients:
			del self.clients[(c.ip, c.port)]



	def server_thread(self):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ServerSock:
			ServerSock.bind((self.ip, self.port))
			ServerSock.listen()
			self.log("server", f"Listening on {self.ip}:{self.port}")
			while self.running:
				ClientSock, ClientAddress = ServerSock.accept()
				if ClientAddress in self.clients:
					self.clients[ClientAddress].sock.close()
					del self.clients[ClientAddress]

				client_obj = Client(
					sock = ClientSock,
					ip = ClientAddress[0],
					port = ClientAddress[1]
					)
				self.clients[ClientAddress] = client_obj
				self.PacketQueue.put((self.current_song_info,[client_obj]))
				self.log("server", f"New client join: {ClientAddress[0]}:{ClientAddress[1]}")

	def log(self, action, string):
		print(f"[{self.name}:{action}] {string}.")

	def shuffle(self):
		random.shuffle(self.songs)
		self.pointer = 0
		self.log("Dj", "Radio has been shuffled")

	def Dj_thread(self):
		while self.running:
			if self.pointer % self.songs_len == 0:
				self.shuffle()
			current_song = self.songs[self.pointer]
			self.log("Dj",f"playing {current_song}")
			self.pointer += 1
			self.AudioStream(current_song)
			#with wave.open(current_song,"rb") as test:
			#	print(test) 
			
if __name__ == "__main__":
	isaacFM = RadioStation("isaacFM", glob.glob("./Songs/*.wav"), port = 5000, ip = "0.0.0.0")
	isaacFM.start()
	isaacFM.join()


