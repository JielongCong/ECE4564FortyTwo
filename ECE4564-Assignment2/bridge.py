from bluetooth import *
import pymongo, time, pika, sys, pickle
import RPi.GPIO as GPIO
import datetime


#IP captured
hostIP=sys.argv[2]

#GPIO setup
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(29, GPIO.OUT)
GPIO.setup(31, GPIO.OUT)
GPIO.setup(33, GPIO.OUT) 
GPIO.output(29, True)
GPIO.output(31, True)
GPIO.output(33, True)

# database client setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["ECE4564"]
collection = db["Assignment2"]

# bluetooth waiting for connection
server_sock=BluetoothSocket( RFCOMM )
server_sock.bind(("",PORT_ANY))
server_sock.listen(5)
port = server_sock.getsockname()[1]                
print ("Waiting for connection on RFCOMM channel" + str(port))

# bluetooth successfully connected
client_sock, client_info = server_sock.accept()
print ("Accepted connection from " + str(client_info))

while 1:
	# White light on
	GPIO.output(29, True)
	GPIO.output(31, True)
	GPIO.output(33, True)
	print('Checkpoint 03' + '[' + str(datetime.datetime.now()) + ']' + ' GPIO LED: White - Waiting for a command.')
	# receive message from bluetooth
	data = client_sock.recv(1024)
	mesg = data.decode()
	mesg= mesg[:-1]
	print('Checkpoint 01' + '[' + str(datetime.datetime.now()) + ']' + ' Message captured: ' + mesg)
	
	# Action
	action = mesg[0]
	# Place
	temp1 = mesg.index(':')
	temp2 = mesg.index('+')
	place = str(mesg[temp1+1:temp2])
	# Subject
	if action == 'p':
		GPIO.output(31, False)
		GPIO.output(33, False)
		print('Checkpoint 03' + '[' + str(datetime.datetime.now()) + ']' + ' GPIO LED: Red - Received publish request.')
		time.sleep(3)
		temp1 = mesg.index('+')
		temp2 = mesg.index(' ')
		subject = str(mesg[temp1+1:temp2])
	elif action == 'c':
		GPIO.output(29, False)
		GPIO.output(31, True)
		GPIO.output(33, False)
		print('Checkpoint 03' + '[' + str(datetime.datetime.now()) + ']' + ' GPIO LED: Green - Received consume request.')
		time.sleep(3)
		temp1 = mesg.index('+')
		subject = mesg[temp1+1:len(mesg)-1]	
	# Message
	if action == 'p':
		temp1 = mesg.index(' ') 
		message = str(mesg[temp1+2:len(mesg)-2])
	elif action =='c':
		message = ""
	# MsgID
	msgID = "20" + "$" + str(time.time())
	#Payload
	payload = {
		"Action" : action,
		"Place"  : place,
		"MsgID"  : msgID,
		"Subject": subject,
		"Message": message
	}
	
	#Insert data to database
	print('Checkpoint 02' + '[' + str(datetime.datetime.now()) + ']' + ' Store command in MongoDB instance: \n' + 'Action = ' + payload['Action'] + '\n' + 
																												  'Place = ' + payload['Place']  + '\n' + 
																												  'MsgID = ' + payload['MsgID']  + '\n' +
																												  'Subject = ' + payload['Subject'] + '\n' +
																												  'Message = ' + payload['Message'])
	collection.insert_one(payload)
	# Blue light on
	GPIO.output(29, False)
	GPIO.output(31, False)
	GPIO.output(33, True)
	print('Checkpoint 03' + '[' + str(datetime.datetime.now()) + ']' + ' GPIO LED: Blue - MongoDB store operation.')
	time.sleep(3)
	
	#RabbitMQ connection set up
	Team = pika.PlainCredentials('team20', 'team20')
	connection = pika.BlockingConnection(pika.ConnectionParameters(host=hostIP, credentials=Team))
	channel = connection.channel()
	#declare
	channel.queue_declare(queue=subject)
	channel.exchange_declare(exchange=place, exchange_type='direct')
	
	print('Checkpoint 04' + '[' + str(datetime.datetime.now()) + ']' + ' Print out RabbitMQ command sent to the Repository RPi: \n' + mesg)
	if action == 'p': #Produce messages into RabbitMQ
		channel.queue_bind(exchange= place,queue= subject, routing_key='hello')	
		channel.basic_publish(
			exchange= place,
			routing_key='hello',
			body= str(message)
		)
		print('Checkpoint 05' + '[' + str(datetime.datetime.now()) + ']' + ' Bridge RPi prints statements generated by the RabbitMQ instance : Produce successfully')
	elif action == 'c': #Consume messages from RabbitMQ
		channel.queue_bind(exchange= place,queue= subject, routing_key='hello')
		while 1:
			exchange, LiuTingjie ,ConsumeMesg = channel.basic_get(subject,True)
			if ConsumeMesg == None:
				break
			temp = ConsumeMesg.decode('utf-8')
			print('Checkpoint 05' + '[' + str(datetime.datetime.now()) + ']' + ' Bridge RPi prints statements generated by the RabbitMQ instance : Consume successfully: '+ temp)

print ("disconnected")
client_sock.close()
server_sock.close()
print ("all done")
