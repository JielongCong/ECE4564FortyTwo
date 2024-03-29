#!/usr/bin/env python3
import tweepy
import socket, pickle, hashlib, os, datetime, sys
from cryptography.fernet import Fernet
from ibm_watson import TextToSpeechV1

# API Keys files
import ClientKeys	

# Basic host setting-up
host = sys.argv[2]
port = int(sys.argv[4])
size = int(sys.argv[6])


text_to_speech = TextToSpeechV1(
	iam_apikey= ClientKeys.Iam_apikey,
	url= ClientKeys.Url
)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('[' + str(datetime.datetime.now()) + ']' + ' Connecting to ' + str(host) + 'on port ' + str(port))

# The stream listener receives tweets from the stream,
# most codes get from: https://realpython.com/twitter-bot-python-tweepy/
class tweetsStreamListener(tweepy.StreamListener):
	def _init_(self,api):
		self.api = api
		self.me = api.me()
	
	def on_status(self, status):
		# Socket setting
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((host,port))
		
		
		# Captured Messages
		print('[' + str(datetime.datetime.now()) + '] New Question: ' + str(status.text))
		text=str(status.text)
		text=text.replace('#ECE4564T20', "")
		text=text.replace("\"", "")
		text=str.encode(text)
		
		# Encrypt Message
		key = Fernet.generate_key()
		f_question_encrypt = Fernet(key)
		token = f_question_encrypt.encrypt(text)
		print ('[' + str(datetime.datetime.now()) + '] Encrypt: Generated Key: ' + str(key) + '| Cipher text: ' + str(token))
		
		# CheckSum
		# Generate a digest for the encrypted message
		# In order to check if there's missing part during the trans
		Hash_question = hashlib.md5()
		Hash_question.update(token)
		Client_Question_checkSum = Hash_question.digest()
		
		# Formatting the payload and serializing
		payload = (key, token, Client_Question_checkSum)
		Question_payload_Serialize = pickle.dumps(payload)
		
		# Send the payload to server via TCP/IP
		print('[' + str(datetime.datetime.now()) + '] Sending data: ' + str(Question_payload_Serialize))
		s.send(Question_payload_Serialize)
		
		# Receive data from server and de-serialize
		data = s.recv(size)
		answer = pickle.loads(data)
		print ('[' + str(datetime.datetime.now()) + '] Received data: ' + str(answer))
		Client_encrypted_ans = answer[0]
		Client_Ans_checkSum = answer[1]
		
		# Re-hash the answer payload
		Rehash_answer = hashlib.md5()
		Rehash_answer.update(Client_encrypted_ans)
		Client_Ans_recheckSum = Rehash_answer.digest()
		
		# Comparing checkSum to see if there's bytes corrupted
		if (Client_Ans_checkSum == Client_Ans_recheckSum):
			f_answer_decrypt = Fernet(key)
			decryptedAns = f_answer_decrypt.decrypt(Client_encrypted_ans)
			decryptedAns = decryptedAns.decode('utf-8')
			print ('[' + str(datetime.datetime.now()) + '] Decrypt: Using Key: ' + str(key) + '| Plain text: ' + str(decryptedAns))
			
		# IBM text-to-speech API
			with open('Answer.mp3', 'wb') as audio_file:
				audio_file.write(
				text_to_speech.synthesize(
				str(decryptedAns),
				voice='en-US_AllisonVoice',
				accept='audio/mp3'        
				).get_result().content)
			
		# Play audio file by using default audio player	
		print ('[' + str(datetime.datetime.now()) + '] Speaking Answer: ' + str(decryptedAns))
		os.system("omxplayer Answer.mp3")
		s.close()
		
	
	def on_error(self, status):
		print("Error detected")

# Authenticate to Twitter
auth = tweepy.OAuthHandler(ClientKeys.APIKey, ClientKeys.APISecretKey)
auth.set_access_token(ClientKeys.Access, ClientKeys.AccessSecret)

# Create API object
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

# Tweepy capturing
print('[' + str(datetime.datetime.now()) + '] Listening for tweets from Twitter API that contain questions')
myStreamListener = tweetsStreamListener(api)
myStream = tweepy.Stream(api.auth, myStreamListener)
myStream.filter(track=["#ECE4564T20"])

s.close()

