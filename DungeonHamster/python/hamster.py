from browser import document, console, window, html
from bisect import bisect_right

#TODO voir si on met tous les binds à la fin d'un seul coup ou si on les laisse répartis.

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

#SECTION fonctions utilitaires
def get_section(elt):
	name=""
	current_node=elt
	while name != "SECTION":
		current_node=current_node.parent
		name=current_node.nodeName
	#TODO exception : si pas dans section
	return current_node

def get_row_info(cellule):
	row = cellule.parent
	row_index=row.rowIndex
	tbody = row.parent
	table = tbody.parent
	nbrows=table.rows.length#TODO ne peut on passer par le tbody au lieu d'interroger la table et les rows de la table?
	return tbody, nbrows, row_index, row

#SECTION gestion des valeurs numériques

#TODO voir pour extraire cela en json si possible, car pure data de config
list_mvt=[{"turn":120,"round":40},{"turn":90,"round":30},{"turn":60,"round":20},{"turn":30,"round":10},{"turn":15,"round":5},{"turn":0,"round":0}]
list_enc_thresh=[0,401,801,1201,1601,2401]

def get_speeds(enc):
	index=bisect_right(list_enc_thresh,enc)-1#bisect_right retourne l'indice de l'élément qui devrait suivre enc si celui-ci était inséré et que la liste devait rester trier, on fait -1 et cela sélectionne donc la valeur immédiatement inférieure à enc
	return list_mvt[index]

def get_section_enc(id):
	#TODO execption si id existe pas
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
	cell_enc=html.TD(Class="Col_Enc", contenteditable="true", inputmode="decimal")#TODO attention le type d'input est à définir aussi sinon il n'y a pas les bons claviers pour les nouvelles lignes
	cell_del=html.TD("✖",Class="Col_Del")
	#on binde les mêmes listeners que pour les cellules de base
	cell_obj.bind("input",when_obj_changed)
	cell_enc.bind("input",when_enc_changed)
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

	if texte_saisi.isnumeric():
		cellule.style.background="MediumSpringGreen"
		tbody, nbrows, row_index, trash=get_row_info(cellule)
		if(row_index==(nbrows-1)):#on est en train de remplir l'enc de la dernière ligne, il faut donc en rajouter une
			make_new_row(tbody)
	else:
		if texte_saisi:
			cellule.style.background="red"
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

list_col_obj=document.getElementsByClassName("Col_Obj")
for i in list_col_obj:
	i.bind("input",when_obj_changed)

#SECTION Gestion de l'activation/inactivation des sections
def when_checkbox_clicked(e):
	case=e.target
	section=get_section(case)
	list_td=section.getElementsByTagName("TD")
	sec_tot = section.getElementsByClassName("Sec_Tot")[0]
	sec_enc = section.getElementsByClassName("Sec_Enc")[0]
	for td in list_td:
		if case.checked:
			#sec_enc.style.color=sec_tot.style.color=""
			#TODO pourquoi la ligne ci-dessus empêche de remettre en vert/rouge plus tard?
			#TODO et pourquoi ça marche maintenant alors que j'ai juste modifié le background?
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


list_checkboxes=document.getElementsByTagName("INPUT")
for i in list_checkboxes:
	i.bind('click',when_checkbox_clicked)