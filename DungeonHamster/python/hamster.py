from browser import document, console, window, html

#SECTION : gestion écartement entre barre du bas et reste du contenu (car la position fixe enlève du flux et empêche donc de scroller assez pour voir tout le tableau le plus bas)
def setMainPadding(*args):#pour avoir des arguments à volonté, comme on ne l'appelle pas forcément avec l'event e (au premier appel au chargement)
	height=document["mainRecap"].height
	main=document["main"]
	#main prend un padding car mettre de la marge à l'invArea ne marchera pas : la marge n'est calculée que si un élément suit, or la barre est fixed donc hors flux
	#on ajoute 1rem au padding car ainsi ça décolle un peu plus
	main.style.paddingBottom=f"calc({height}px + 1rem)"

#on appelle une première fois la fonction d'écartement au chargement de la page
setMainPadding()
#on la binde au redimmensionnement de la fenêtre
window.bind('resize', setMainPadding)

#SECTION gestion du remplissage des rows des tables
def newRow(tbody):
	console.log("i fucking love you john")
	newRow=html.TR()
	cellObj=html.TD(Class="colObj", contenteditable="true")
	cellEnc=html.TD(Class="colEnc", contenteditable="true")
	cellDel=html.TD("✖",Class="colDel")
	#on binde les mêmes listeners que pour les cellules de base
	cellEnc.bind("input",validate)
	cellDel.bind('click',delLigne)
	newRow.appendChild(cellObj)
	newRow.appendChild(cellEnc)
	newRow.appendChild(cellDel)
	tbody.appendChild(newRow)


#def getRowInfo(cellule):


def validate(e):
	cellule = e.target
	texteSaisi = cellule.textContent
	if texteSaisi.isnumeric():
		cellule.style.background="aquamarine"
		row = cellule.parent
		row_index=row.rowIndex
		tbody = row.parent
		table = tbody.parent
		nbrows=table.rows.length
		if(row_index==(nbrows-1)):
			newRow(tbody)
	else:
		e.target.style.background="red"






listColEnc=document.getElementsByClassName("colEnc")
for i in listColEnc:
	i.bind("input",validate)






#SECTION suppression des lignes
def delLigne(e):
	cellule=e.target
	row = cellule.parent
	index=row.rowIndex
	tbody=row.parent
	table = tbody.parent
	nbrows=table.rows.length
	row.remove()
	if index<2 and nbrows<3:#première et unique ligne, on la recrée immédiatement
		newRow(tbody)



listColdDev=document.getElementsByClassName("colDel")
for i in listColdDev:
	#console.log(i)
	i.bind('click',delLigne)