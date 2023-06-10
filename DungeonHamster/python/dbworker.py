from browser import self, console

def when_messaged(e):
	print("in worker!!!!!!!!!!!!!")
	reply={"turn":90,"round":30}
	self.send(reply)
	
self.bind('message',when_messaged)
