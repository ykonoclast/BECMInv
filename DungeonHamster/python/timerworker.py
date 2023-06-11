from browser import self, console, timer

typing_timer = 0
typing_interval = 3000
row_desc=0
MSG_RESTART="restart"

def timer_expired():
	sec_id=row_desc["section"]
	dbkey=row_desc["dbkey"]
	console.log(f"Timer worker : desc={sec_id};{dbkey} : TIMER EXPIRED")
	self.send(row_desc)
	self.close()


def when_messaged(msg):
	global typing_timer #sinon ce sera une variable locale pour la modification!
	global row_desc
	stage = "INIT"

	if msg.data!=MSG_RESTART:#on est à l'initialisation
		row_desc=msg.data
	else:#le worker était déjà en route, le message indique juste de redémarrer le timer
		timer.clear_timeout(typing_timer)
		stage="RESTART"

	sec_id=row_desc["section"]
	dbkey=row_desc["dbkey"]
	console.log(f"Timer worker : desc={sec_id};{dbkey} : TIMER {stage}")
	typing_timer = timer.set_timeout(timer_expired, typing_interval)

self.bind('message',when_messaged)