from browser import document, console, window, html

#TODO les noms des fonctions et variables partent dans tous les sens, clarifier

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

#SECTION creation et suppression des rows des tables
def newRow(tbody):
	newRow=html.TR()
	cellObj=html.TD(Class="colObj", contenteditable="true")
	cellEnc=html.TD(Class="colEnc", contenteditable="true")#TODO attention le type d'input est à définir aussi sinon il n'y a pas les bons claviers pour les nouvelles lignes
	cellDel=html.TD("✖",Class="colDel")
	#on binde les mêmes listeners que pour les cellules de base
	cellObj.bind("input",whenObjChanged)
	cellEnc.bind("input",whenEncChanged)
	cellDel.bind('click',delRow)
	newRow.appendChild(cellObj)
	newRow.appendChild(cellEnc)
	newRow.appendChild(cellDel)
	tbody.appendChild(newRow)

def getRowInfo(cellule):
	row = cellule.parent
	row_index=row.rowIndex
	tbody = row.parent
	table = tbody.parent
	nbrows=table.rows.length#TODO ne peut on passer par le tbody au lieu d'interroger la table et les rows de la table?
	return tbody, nbrows, row_index, row

def checkDelRow(cellule):
	tbody,nbrows,index,row=getRowInfo(cellule)
	row.remove()
	if index<2 and nbrows<3 or index==nbrows-1:#première et unique ligne ou dernière, on la recrée immédiatement
		newRow(tbody)#TODO ne pas supprimer plutôt? A voir car il y a le cas du juste clear (premiere ligne seule)

def preCheckDelRow(cellule, isEncCol):
	row=cellule.parent
	index=0
	if not(isEncCol):
		index=2
	otherCell=row.childNodes[index]
	if otherCell.textContent:
		if isEncCol:#TODO le recheck de la même variable est assez dégueulasse
			manageText(cellule)
	else:
		checkDelRow(cellule)

def delRow(e):
	checkDelRow(e.target)

listColdDev=document.getElementsByClassName("colDel")
for i in listColdDev:
	i.bind('click',delRow)

#SECTION gestion du remplissage des rows des tables
def manageText(cellule):
	if cellule.textContent.isnumeric():
		cellule.style.background="aquamarine"
		tbody, nbrows, row_index, trash=getRowInfo(cellule)
		if(row_index==(nbrows-1)):
			newRow(tbody)
	else:
		cellule.style.background="red"

def validate(e,isEncCol):
	cellule = e.target
	if cellule.textContent:
		if isEncCol:
			manageText(cellule)
	else:
		preCheckDelRow(cellule,isEncCol)

def whenObjChanged(e):
	validate(e, False)

def whenEncChanged(e):
	validate(e,True)



listColEnc=document.getElementsByClassName("colEnc")
for i in listColEnc:
	i.bind("input",whenEncChanged)

listColObj=document.getElementsByClassName("colObj")
for i in listColObj:
	i.bind("input",whenObjChanged)