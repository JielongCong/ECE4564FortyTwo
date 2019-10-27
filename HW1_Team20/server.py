#!/usr/bin/env python3

import socket, pickle, hashlib, os, datetime, sys
from cryptography.fernet import Fernet
from ibm_watson import TextToSpeechV1
import json
import wolframalpha
import ServerKeys

host = '172.30.8.128'
port =  int(sys.argv[2])
backlog = 5
size = int(sys.argv[4])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('[' + str(datetime.datetime.now()) + ']' + ' Created socket at ' + str(host) + ' on port ' + str(port))
s.bind((host, port))
s.listen(backlog)
print('[' + str(datetime.datetime.now()) + ']' + ' Listening for client connections')

text_to_speech = TextToSpeechV1(
	iam_apikey=ServerKeys.Iam_apikey,
	url=ServerKeys.Url
)

wolf_client = wolframalpha.Client(ServerKeys.wolfKey)
	
while 1:
	# Receive payload from the client
	client,address = s.accept()
	print('[' + str(datetime.datetime.now()) + ']' + ' Accepted client connection from ' + str(host) + 'on port ' + str(port))
	data= client.recv(size)
	print('[' + str(datetime.datetime.now()) + ']' + ' Received data: ' + str(data))
	
	# De-serialize payload
	question = pickle.loads(data)
	key = question[0]
	encryptedMes = question[1]
	Server_Question_checkSum = question[2]
	
	# Re-hash the encrypted message
	Rehash_question = hashlib.md5()
	Rehash_question.update(encryptedMes)
	Server_Question_recheckSum = Rehash_question.digest()
	
	# Comparing checkSum to see if there's bytes corrupted
	if (Server_Question_checkSum == Server_Question_recheckSum):
		f_question_decrypt = Fernet(key)
		decryptedMes = f_question_decrypt.decrypt(encryptedMes)
		decryptedMes = decryptedMes.decode('utf-8')
		print('[' + str(datetime.datetime.now()) + ']' + ' Decrypt: ' + str(key) + ' | Plain text: ' + str(decryptedMes))
		
		# IBM text-to-speech API
		with open('Question.mp3', 'wb') as audio_file:
			audio_file.write(
			text_to_speech.synthesize(
			str(decryptedMes),
			voice='en-US_AllisonVoice',
			accept='audio/mp3'        
			).get_result().content)
			
		# Play audio file by using default audio player	
		print('['+ str(datetime.datetime.now()) + ']' + ' Speaking Question: ' + str(decryptedMes))
		os.system("omxplayer Question.mp3")
		
		# Get answer from WolframeAlpha API
		print('[' + str(datetime.datetime.now()) + ']' + ' Sending question to Wolframalpha: ' + str(decryptedMes))
		res = wolf_client.query('Question: ' + decryptedMes)
		ans = next(res.results).text
		print('[' + str(datetime.datetime.now()) + ']' + ' Received answer from Wolframalpha: ' + str(ans))
		ans = str.encode(ans)
			
		# Encrypt and hash answer 
		f_answer_encrypt = Fernet(key)
		Server_encrypted_ans = f_answer_encrypt.encrypt(ans)
		print('[' + str(datetime.datetime.now()) + ']' + ' Encrypt: Key: ' + str(key) + ' | Ciphertext: ' + str(Server_encrypted_ans))
		m_ans = hashlib.md5()
		m_ans.update(Server_encrypted_ans)
		Server_Ans_checkSum = m_ans.digest()
		print('[' + str(datetime.datetime.now()) + ']' + ' Generated MD5 Checksum: ' + str(Server_Ans_checkSum))
		
		# Formatting answer payload and serialize it
		ans_payload = (Server_encrypted_ans, Server_Ans_checkSum)
		Serialized_ans_payload = pickle.dumps(ans_payload)
		
		#Send serialized answer payload to client
		print('[' + str(datetime.datetime.now()) + ']' + ' Sending answer: ' + str(Serialized_ans_payload))
		client.send(Serialized_ans_payload)
		client.close()
					
	else:
		print("Error: Corrupted Message")
		
	
