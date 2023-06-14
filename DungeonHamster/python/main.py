from browser import document, console, window, html, alert, worker
from bisect import bisect_right
from queue import Queue
import javascript

#NOTE GÉNÉRALE : peu de gestion d'erreur (il faut dire que généralement s'il y a un problème on veut juste que ça continue à tourner)
# de plus le browser logge déjà les erreurs lui-même...
# néanmoins peu satisfaisant, les prochains projets devront faire mieux

#TODO ajouter en var globales les noms de classes css en cas de changement
DB_NAME="DungeonDB"
DB_VERSION=1
DB_SEC_STORE="in-act_sections"
MSG_RESTART="restart"
list_mvt=[{"turn": 120,"round": 40}, {"turn": 90,"round": 30}, {"turn": 60,"round": 20}, {"turn": 30,"round": 10}, {"turn": 15,	"round": 5}, {"turn": 0,"round": 0}]
list_enc_thresh=[0, 401, 801, 1201, 1601, 2401]

list_active_sections = [x.id for x in document.getElementsByClassName("Active_Section")]
list_inactive_sections = [x.id for x in document.getElementsByClassName("Inactive_Section")]
list_all_sections =list_active_sections+list_inactive_sections

#SECTION fonctions utilitaires
def get_section(elt):
	name=""
	current_node=elt
	while name != "SECTION":
		current_node=current_node.parent
		name=current_node.nodeName
	return current_node

def get_row_info(cellule):
	row = cellule.parent
	row_index=row.rowIndex
	tbody = row.parent
	table = tbody.parent
	nbrows=table.rows.length#TODO ne peut on passer par le tbody au lieu d'interroger la table et les rows de la table?
	return tbody, nbrows, row_index, row

#SECTION : persistance des données
db = 0

def del_row_db(sec_id,dbkey):
	transaction = db.transaction(sec_id,"readwrite")#on limite la transaction au store d'intérêt pour pers
	store = transaction.objectStore(sec_id)
	console.log(f"DB: erasing row in store {sec_id} with {dbkey}")
	store.delete(dbkey)

def save_status_db(checked, sec_id):
	transaction = db.transaction(DB_SEC_STORE,"readwrite")
	store = transaction.objectStore(DB_SEC_STORE)
	console.log(f"DB: saving {sec_id} status {checked}")
	store.put(checked,sec_id)

def create_datapack(row):
	obj_cell = row.getElementsByClassName("Col_Obj")[0]
	obj_text = obj_cell.text
	enc_cell = row.getElementsByClassName("Col_Enc")[0]
	enc_text = enc_cell.text
	data = {"obj": obj_text,"enc": enc_text}
	return data

def when_typing_done(row_desc):
	sec_id = row_desc["section"]
	dbkey=row_desc["dbkey"]

	section = document[sec_id]
	rows = section.getElementsByTagName("TR")
	row=0
	for r in rows:
		if hasattr(r,"dbkey"):#un row persisté
			if r.dbkey==dbkey:
				row=r
	if row!=0:#le row dont le timer vient d'expirer est toujours bien là
		if db!=0:#la requête d'ouverture est passée
			data = create_datapack(row)
			console.log(f"DB: updating row in section {sec_id} with key {dbkey} and value {data}")
			transaction = db.transaction(sec_id,"readwrite")#on limite la transaction au store d'intérêt pour pers
			store = transaction.objectStore(sec_id)
			store.put(data,row.dbkey)

#Une fois le row pour la première fois persisté, on y inscrit sa clé via cette callback pour les updates ultérieures
def write_key_in_row(e):
	row = e.target.row_persisted
	row.dbkey = e.target.result
	row.dblock=False

def init_row_db(sec_id,row):
	transaction = db.transaction(sec_id,"readwrite")
	store = transaction.objectStore(sec_id)
	data = create_datapack(row)
	console.log(f"DB: creating {data} in store {sec_id}")
	req = store.add(data)
	req.row_persisted = row #(IMPORTANT) l'objet sur lequel on binde EST le target passé à la callback DONC on ajoute à la requête un attribut : le row, comme cela la clé générée pourra y être inscrite dans la callback
	req.bind("success", write_key_in_row)#on n'utilise pas ici une closure en callback car je ne suis pas sûr de comment le contexte sera maintenu : row peut-il changer si la fonction englobante est appelée AVANT l'exécution de la callback? Mieux vaut utiliser la technique de l'attribut supplémentaire dans la requête

#les événements n'ayant pu être traités car la DB n'était pas encore ouverte
event_queue=Queue()

#Fonction centrale pour la gestion de la persistance. Le fonctionnement est le suivant:
#L'événement "keyup" fait entrer dans la fonction, on teste alors si le row a déjà été persisté
#si ce n'est pas le cas : l'utilisateur a tapé le premier caractère dedans, on l'envoie tout de suite en base pour obtenir une clé (car on ne va pas générer un identifiant unique dans le code et aucun attribut ne se prête à être une clé, on envoie donc une première transaction avec le premier caractère pour que la base génère un identifiant, le mécanisme des timers fonctionnant par la suite)
#si c'est le cas, on va lancer un timer via un webworker pour laisser le temps de compléter la saisie avant d'envoyer le row entier en base
def when_keyup(e):
	cellule = e.target
	section = get_section(cellule)
	sec_id = section.id
	tbody,nbrows,index,row=get_row_info(cellule)

	if db!=0:#la requête d'ouverture est passée
		if hasattr(row,"dbkey"):#le row a déjà été persisté
			dbkey = row.dbkey
			create_worker=True
			try:#au cas où worker_dict existe déjà
				if dbkey in when_keyup.worker_dict[sec_id]:#le row possède un worker actif, on n'en crééra donc pas de nouveau
					create_worker=False
					if when_keyup.worker_dict[sec_id][dbkey]!=0:#le worker est déjà initialisé, on peut donc le relancer (sinon c'est inutile, on attend juste)
						timer_worker = when_keyup.worker_dict[sec_id][dbkey]
						timer_worker.send(MSG_RESTART)
			except:#pas de worker_dict : on l'initialise
				when_keyup.worker_dict={key:{} for key in list_all_sections}#comprehension de dict : différent de la création avec dict.fromkeys qui aurait donné le MÊME dico vide à toutes les clés : entraînant modif de masse de toutes les entrées d'un coup à chaque assignation, avec la comprehension on aura un dico vide DIFFERENT à chaque fois
			if create_worker:#pas de worker actif, on le crée
				row_desc={"section":sec_id,"dbkey":dbkey}
				try:#au cas où la queue existe déjà
					when_keyup.worker_queue.put(row_desc)
				except:#pas de queue : on l'initialise
					when_keyup.worker_queue=Queue()
					when_keyup.worker_queue.put(row_desc)

				#appelée en fin de timer, va déclencher la mise à jour de la base
				def worker_message(msg):#closure pour garder le contexte de worker_dict
					row_desc=msg.data
					sec_id=row_desc["section"]
					dbkey=row_desc["dbkey"]
					#on supprime le worker du dictionnaire des workers actifs
					if dbkey in when_keyup.worker_dict[sec_id]:
						when_keyup.worker_dict[sec_id].pop(dbkey)
					when_typing_done(row_desc)

				#callback à l'initialisation du worker, pour le configurer et l'enregistrer dans les workers actifs
				def worker_ready(new_worker):
					row_desc=when_keyup.worker_queue.get()#garantie d'y trouver quelque chose : on ne lance un worker qu'après avoir peuplé la queue
					new_worker.send(row_desc)#config du worker
					sec_id = row_desc["section"]
					dbkey =row_desc["dbkey"]
					when_keyup.worker_dict[sec_id][dbkey]=new_worker#enregistrement du worker

				#on signale qu'un worker est en train de s'initialiser, pour ne pas risquer d'en créer un deuxième avant que le premier n'ait complètement démarré
				when_keyup.worker_dict[sec_id][dbkey]=0
				#on crée le worker avec les deux callback closures définies ci-dessus
				worker.create_worker("timerworker", worker_ready, worker_message)
		else:#le row n'a jamais été persisté, on va le créer pour avoir une clé
			go=True#on vérifie que le row n'est pas en train d'être inscrit en base car on ne maîtrise pas le temps qu'il faudra pour appeler write_key_in_row en callback
			if hasattr(row,"dblock"):
				if row.dblock:
					go=False
			if go:
				row.dblock=True
				init_row_db(sec_id,row)
	else:
		console.warn("DB: can't write in {sec_id}, database closed ; event queued")
		event_queue.put(e)#on sauvegarde l'événement : on le relancera plus tard quand la base sera prête

def restore_section(e):
	sec_id = e.target.sec_id
	section=document[sec_id]
	list_tbody=section.getElementsByTagName("TBODY")
	tbody=list_tbody[0]
	store_content = e.target.result

	if store_content:#il y a une ligne à insérer
		#try:#pythonic : "better to ask for forgiveness than permission", on essaye d'appeler une variable statique de la fonction (qui persiste entre les appels), si elle n'existe pas, une exception est levée et on l'initialise donc
		#	if sec_id in restore_section.wasnum:
		#		if not restore_section.wasnum[sec_id]:#la dernière ligne de la section actuelle n'était pas numérique : il faut donc créer une ligne vide
		#			make_new_row(tbody)
		#except:
			#restore_section.wasnum={}
		dbkey=store_content.key
		rowdata=javascript.JSObject.to_dict(store_content.value)
		list_tr=tbody.getElementsByTagName("TR")
		lastrow=list_tr[-1]
		lastrow.dbkey=dbkey
		obj_cell = lastrow.getElementsByClassName("Col_Obj")[0]
		obj_cell.text = rowdata["obj"]
		enc_cell = lastrow.getElementsByClassName("Col_Enc")[0]
		enc_cell.text=rowdata["enc"]
		validate_enc(enc_cell)
		#make_new_row(tbody)
		#check de si la ligne insérée était numérique, pour l'éventuel coup d'après
		#text_check=enc_cell.text
		#if text_check.isnumeric():
		#	restore_section.wasnum[sec_id]=True
		#else:
		#	restore_section.wasnum[sec_id]=False

		#bricolage pour appeler la fonction javascript "continue" sur le cursor et refaire un cycle
		cont = getattr(store_content, "continue")
		cont()

	else:#on a fini de remplir la section, on restaure maintenant son état activé ou non
		transaction = db.transaction(DB_SEC_STORE,"readonly")
		store = transaction.objectStore(DB_SEC_STORE)
		countreq = store.count(sec_id)

		def check_section_status(e):#callback en closure pour garder le contexte de sec_id
			keycount = e.target.result
			if keycount>0:
				checkedreq=store.get(sec_id)
				def restore_section_status(e):#callback en closure pour garder le contexte de section
					checked = e.target.result
					listcases = section.getElementsByTagName("INPUT")
					case=listcases[0]
					if checked:
						case.setAttribute("checked", "true")
					else:
						case.removeAttribute("checked")
					flip_section(case)

				checkedreq.bind("success",restore_section_status)
		countreq.bind("success",check_section_status)

def upgradeDB(event):#base de données de nom inconnu ou de version n'existant pas : on construit le schéma
	console.groupCollapsed("DB: upgrade needed, creating object stores")
	db = event.target.result#event.target est la REQUÊTE IndexedDb ; ici le résultat de la requête (d'ouverture) est la base elle-même
	for section in list_all_sections:#on crée un store par section
		db.createObjectStore(section, { "autoIncrement": True })#store sans index (on n'interrogera jamais sur les colonnes), autoincrement pour clé technique autoconstruite (car on peut pas utiliser rowindex : il change avec suppressions) ou de keypath ; voir la doc : beaucoup d'implications sur les keypath et les keygenerators (notamment uniquement objets JS si keypath)
		console.log(f"store:{section}")
	db.createObjectStore(DB_SEC_STORE)#nouveau store, pour grisage/dégrisage des sections, pas de clé autogénérée : les id de section sont uniques
	console.log(f"store:{DB_SEC_STORE}")
	console.groupEnd()

def when_db_opened(event):#sera forcément appelé après upgradeDB car l'event success arrive toujours après le traitement de upgradeneeded
	version = event.target.result.version
	if version != DB_VERSION:#la version déjà installée n'est pas la dernière, on la supprime et on rouvre une nouvelle base avec la bonne version
		console.log(f"DB: older version ({version}) will be deleted then current version({DB_VERSION} will be created)")
		event.target.result.close()
		window.indexedDB.deleteDatabase(DB_NAME)
		open_db(True)
	else :#setup from DB
		console.groupCollapsed("DB: successfully opened, restoring sections")
		global db
		db = event.target.result;
		transaction = db.transaction(list_all_sections,"readonly")
		for section in list_all_sections:
			console.log(f"Section:{section}")
			store = transaction.objectStore(section)
			strequest = store.openCursor()
			strequest.sec_id=section
			strequest.bind("success",restore_section)
		console.groupEnd()
		while not event_queue.empty():#traitement des événements keyup lancés pendant que la base n'était pas encore ouverte
			e=event_queue.get()
			console.log("DB: treating a stored event")
			when_keyup(e)

def open_db(withVersion):
	console.groupCollapsed("DB: Opening...")
	if withVersion:
		console.log(f"Version={DB_VERSION}")
		dbrequest = window.indexedDB.open(DB_NAME,DB_VERSION)
	else:
		console.log("Version=last installed")
		dbrequest = window.indexedDB.open(DB_NAME)
	dbrequest.bind("upgradeneeded", upgradeDB)
	dbrequest.bind("success", when_db_opened)
	console.groupEnd()

idb_present=False
persist_present=False
persist_granted=True

def app_boot():
	msg=""
	if not persist_present:
		msg+="Persistance non supportée par le navigateur, les données pourront être effacées entre deux démarrages par le nettoyage automatique du cache.\n"
	else:
		if not persist_granted:
			msg+="Persistance non accordée par le navigateur, les données pourront être effacées entre deux démarrages par le nettoyage automatique du cache.\n"
	if not idb_present:
		msg+="IndexedDB non supportée par le navigateur, les données ne seront pas sauvegardées entre deux démarrages de l'application."
	else:
		open_db(False)#false pour ne pas spécifier de version (cf. fonction appelée) afin de récupérer la base déjà installée, quelle que soit la version, afin de détecter l'emploi d'une éventuelle vieille version à supprimer
	if msg!="":
		alert(msg)

#Ouverture de la base de données
def disp_persist(granted):
	global persist_granted
	persist_granted=granted
	app_boot()#on passe quoi qu'il arrive au démarrage de l'appli

if hasattr(window,"indexedDB"):
	idb_present=True

navigator = window.navigator
if hasattr(navigator, "storage") and hasattr(navigator.storage,"persist"):
	persist_present=True
	navigator.storage.persist().then(disp_persist,app_boot)#si persistance, on traite, sinon on skippe direct au démarrage de l'appli

#SECTION : gestion écartement entre barre du bas et reste du contenu (car la position fixe enlève du flux et empêche donc de scroller assez pour voir tout le tableau le plus bas)
def set_main_padding(*args):#pour avoir des arguments à volonté, comme on ne l'appelle pas forcément avec l'event e (au premier appel au chargement)
	height=document["main_recap_id"].height
	main=document["main_id"]
	#main prend un padding car mettre de la marge à l'Inv_Area ne marchera pas : la marge n'est calculée que si un élément suit, or la barre est fixed donc hors flux
	#on ajoute 1rem au padding car ainsi ça décolle un peu plus
	main.style.paddingBottom=f"calc({height}px + 1rem)"

#on appelle une première fois la fonction d'écartement au chargement de la page
set_main_padding()
#on la binde au redimmensionnement de la fenêtre
window.bind('resize', set_main_padding)

#SECTION gestion des valeurs numériques
def get_speeds(enc):
	index=bisect_right(list_enc_thresh,enc)-1#bisect_right retourne l'indice de l'élément qui devrait suivre enc si celui-ci était inséré et que la liste devait rester trier, on fait -1 et cela sélectionne donc la valeur immédiatement inférieure à enc
	return list_mvt[index]

def get_section_enc(id):
	recap = document[id]
	sec_tot = recap.getElementsByClassName("Sec_Tot")[0]
	return int(sec_tot.text)

def update_main_recap():
	sacdos=get_section_enc("recap_sacdos_id")
	grossac=get_section_enc("recap_grossac_id")
	bourse=get_section_enc("recap_bourse_id")
	petitsac1=get_section_enc("recap_petitsac1_id")
	petitsac2=get_section_enc("recap_petitsac2_id")
	petitsac3=get_section_enc("recap_petitsac3_id")
	porte=get_section_enc("recap_porte_id")

	total = sacdos + grossac + bourse + petitsac1 + petitsac2 + petitsac3 + porte
	sanssacdos = total - sacdos
	sanssacsclass = total - petitsac1 - petitsac2 - petitsac3 - grossac
	justebourseporte = porte + bourse

	document["total_id"].text=total
	document["sanssacdos_id"].text=sanssacdos
	document["sanssacsclass_id"].text=sanssacsclass
	document["justebourseporte_id"].text=justebourseporte

	total_speed_byturn, total_speed_byround = get_speeds(total).values()
	sanssacdos_speed_byturn, sanssacdos_speed_byround = get_speeds(sanssacdos).values()
	sanssacsclass_speed_byturn, sanssacsclass_speed_byround = get_speeds(sanssacsclass).values()
	justebourseporte_speed_byturn, justebourseporte_speed_byround = get_speeds(justebourseporte).values()

	document["total_byround_id"].text=total_speed_byround
	document["sanssacdos_byround_id"].text=sanssacdos_speed_byround
	document["sanssacsclass_byround_id"].text=sanssacsclass_speed_byround
	document["justebourseporte_byround_id"].text=justebourseporte_speed_byround

	document["total_byturn_id"].text=total_speed_byturn
	document["sanssacdos_byturn_id"].text=sanssacdos_speed_byturn
	document["sanssacsclass_byturn_id"].text=sanssacsclass_speed_byturn
	document["justebourseporte_byturn_id"].text=justebourseporte_speed_byturn

def update_enc(section):
	#calcul du contenu de l'emplacement
	sec_enc=section.getElementsByClassName("Sec_Enc")[0]
	list_enc=section.getElementsByClassName("Col_Enc")

	items_total = sum(int(x.text) for x in list_enc if x.text.isnumeric())
	sec_enc.text=items_total

	#prise en compte de l'encombrement intrinsèque
	enc_intr=0
	list_sec_intr=section.getElementsByClassName("Sec_Intr")
	if list_sec_intr:#liste non vide : il y a donc une valeur intrinsèque pour cet emplacement
		sec_intr=list_sec_intr[0]
		enc_intr=int(sec_intr.text)

	#affichage du total
	sec_tot = section.getElementsByClassName("Sec_Tot")[0]
	sec_tot.text=items_total+enc_intr

	#validation des entrées
	color=""#comme cela, si aucun cas, la couleur redevient par défaut
	if items_total!=0:
		list_sec_max=section.getElementsByClassName("Sec_Max")
		color="MediumSpringGreen"
		if list_sec_max:
			sec_max=list_sec_max[0]
			maxi=int(sec_max.text)
			if items_total>maxi:
				color="red"

	sec_enc.style.color=sec_tot.style.color=color

	#mise à jour du récap total en bas
	update_main_recap()

#SECTION creation et suppression des rows des tables
def make_new_row(tbody):
	new_row=html.TR()
	cell_obj=html.TD(Class="Col_Obj", contenteditable="true")
	cell_enc=html.TD(Class="Col_Enc", contenteditable="true", inputmode="decimal")
	cell_del=html.TD("✖",Class="Col_Del")
	#on binde les mêmes listeners que pour les cellules de base
	cell_obj.bind("input",when_obj_changed)
	cell_obj.bind("keyup",when_keyup)
	cell_enc.bind("input",when_enc_changed)
	cell_enc.bind("keyup",when_keyup)
	cell_del.bind('click',when_del_clicked)
	new_row.appendChild(cell_obj)
	new_row.appendChild(cell_enc)
	new_row.appendChild(cell_del)
	tbody.appendChild(new_row)

def del_row(cellule):
	tbody,nbrows,index,row=get_row_info(cellule)
	section=get_section(cellule)
	row.remove()
	if index<2 and nbrows<3 or index==nbrows-1:#première et unique ligne ou dernière, on la recrée immédiatement
		#TODO voir si on peut tout de même pas THEAD et modifier alors ces valeurs d'index (avec tbody plutôt que table dans le css)
		make_new_row(tbody)
	update_enc(section)

	if hasattr(row, "dbkey"):#le row est persisté, il faut le supprimer de la base
		del_row_db(section.id, row.dbkey)

def check_row_todel(cellule, is_enc_col):
	row=cellule.parent
	other_class_name="Col_Obj" if is_enc_col else "Col_Enc"
	other_cell=row.getElementsByClassName(other_class_name)[0]
	if other_cell.text:
		if is_enc_col:
			update_enc(get_section(cellule))
			cellule.style.background=None
	else:
		del_row(cellule)

def when_del_clicked(e):
	del_row(e.target)

list_col_del=document.getElementsByClassName("Col_Del")
for i in list_col_del:
	if (get_section(i).class_name=="Active_Section"):
		i.bind('click',when_del_clicked)

#SECTION gestion du remplissage des rows des tables
def validate_enc(cellule):
	list_BR=cellule.getElementsByTagName("BR")
	for i in list_BR:#suppression des sauts de ligne
		i.remove()
	texte_saisi=cellule.text

	if texte_saisi:
		if texte_saisi.isnumeric():
			cellule.style.background="MediumSpringGreen"
		else:
			cellule.style.background="red"
		tbody, nbrows, row_index, trash=get_row_info(cellule)
		if(row_index==(nbrows-1)):#on est en train de remplir l'enc de la dernière ligne, il faut donc en rajouter une
			make_new_row(tbody)

	update_enc(get_section(cellule))#on appelle toujours l'update de l'enc car on peut avoir rendu non-numérique une cellule l'étant antérieurement

def check_text_changed(e,is_enc_col):
	cellule = e.target
	if cellule.text:
		if is_enc_col:
			validate_enc(cellule)
	else:
		check_row_todel(cellule,is_enc_col)

def when_obj_changed(e):
	check_text_changed(e, False)

def when_enc_changed(e):
	check_text_changed(e,True)

list_col_enc=document.getElementsByClassName("Col_Enc")
for i in list_col_enc:
	i.bind("input",when_enc_changed)
	i.bind("keyup",when_keyup)

list_col_obj=document.getElementsByClassName("Col_Obj")
for i in list_col_obj:
	i.bind("input",when_obj_changed)
	i.bind("keyup",when_keyup)

#SECTION Gestion de l'activation/inactivation des sections
def when_checkbox_clicked(e):
	case=e.target
	flip_section(case)

def flip_section(case):
	section=get_section(case)
	list_td=section.getElementsByTagName("TD")
	sec_tot = section.getElementsByClassName("Sec_Tot")[0]
	sec_enc = section.getElementsByClassName("Sec_Enc")[0]
	for td in list_td:
		if case.checked:
			section.class_name="Active_Section"
			if td.class_name=="Col_Del":
				td.bind('click',when_del_clicked)
			else:
				td.setAttribute("contenteditable", True)
				if td.class_name=="Col_Enc":
					td.setAttribute("inputmode","numeric")
					validate_enc(td)
		else:
			section.class_name="Inactive_Section"
			if td.class_name=="Col_Del":
				td.unbind('click',when_del_clicked)
			else:
				td.setAttribute("contenteditable", False)
				if td.class_name=="Col_Enc":
					td.style.background="transparent"
			sec_enc.style.color=sec_tot.style.color="#888"

			#neutralisation de l'encombrement
			sec_tot.text=0
			update_main_recap()
	#persistance en base
	save_status_db(case.checked, section.id)

list_checkboxes=document.getElementsByTagName("INPUT")
for i in list_checkboxes:
	i.bind('click',when_checkbox_clicked)