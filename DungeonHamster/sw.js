//Note : le manifest.json possède comme valeur d'orientation "any" ce qui permet la roation de l'écran


const CACHE_VERSION = "vALPHA18";//TODO aussi changer la version du cache à terme
//Noter ci-dessous la présence de /, pas certain que ça marche avec index.html
const LIST_PRE_CACHE = ["/", "favicon.ico", "manifest.json", "css/styles.css", "python/main.py", "python/timerworker.py", "js/brython.js", "js/brython_stdlib.js", "icons/logo.png", "icons/logo192.png", "icons/logo512.png", "fonts/EBGaramond-Italic.otf", "fonts/EBGaramond-Regular.otf", "fonts/EBGaramond-SemiBold.otf"];


//Noter que l'on pourrait se passer du pré-cache dans la mesure où l'appli est simple : tout est donc fetché rapidement dès le début (et donc serait mis en cache ainsi). Mais pour une appli plus compliquée il faut pré-cacher les assets qui ne sont pas forcément fetchés dès le début si l'on veut plus tard y accéder hors ligne avant qu'un fetch réseau ne soit arrivé
//cette fonction est async surtout pour renvoyer une promesse sur laquelle pourra attendre le event.waituntil de when_install : sinon dans l'absolu il n'y aurait rien de choquant à ce qu'elle soit, justement, synchrone, pour finir de bien charger le cache avant d'aller plus loin.
async function pre_cache()//la fonction async attendra sur des await pendant que le thread principal continue, checkant le await au prochain tick
{
	try
	{
		console.log(`SW:Pre-caching for cache ${CACHE_VERSION}...`);
		//le couple "const" et "await" remplace ce qui se trouve respectivement après et avant le "then" en syntaxe de promise (en ce cas : caches.open(CACHE_VERSION).then(cache=>cache.addALL(LIST_PRE_CACHE))
		const currentCache = await caches.open(CACHE_VERSION);//pas d'attente active sur l'ouverture du cache
		await currentCache.addAll(LIST_PRE_CACHE);
	}
	catch (e)
	{
		console.error(e);
	}
}

function when_install(event)
{
	self.skipWaiting();//on n'attend pas la fin de vie du précédent service worker : on le supprime pour installer le nouveau directement.
	console.log("SW:Service Worker installing...");
	try
	{
		event.waitUntil(pre_cache());//le service worker ne passera au stade d'ACTIVATION que APRÈS tous les traitements de pré-cache
	}
	catch (e)
	{
		console.error(e);
	}
}

self.addEventListener("install", when_install);



async function delete_single_cache(key)
{
	try
	{
		console.log(`SW:Deleting older cache ${key}...`);
		await caches.delete(key);
	}
	catch (e)
	{
		console.error(e);
	}
}

//cette fonction est async surtout pour renvoyer une promesse sur laquelle pourra attendre le event.waituntil de when_activate : sinon dans l'absolu il n'y aurait rien de choquant à ce qu'elle soit, justement, synchrone, pour finir de bien nettoyer le cache avant d'aller plus loin.
async function delete_older_caches()
{
	try
	{
		const cacheKeys = await caches.keys();
		keysToDelete = cacheKeys.filter(key => key !== CACHE_VERSION);
		await Promise.all(keysToDelete.map(delete_single_cache));//le promise.all groupe toutes les promesses du tableau, donc on attend la suppression de toutes les clés pour sortir de la méthode ; la fonction n'est pas async MAIS promise.all wrappera le résultat dans une promesse donc ça va.
	}
	catch (e)
	{
		console.error(e);
	}
}



function when_activate(event)
{
	console.log("Service Worker activating...");
	//claim() renvoie une promise, on pourrait faire un await dessus, mais de toute façon on va faire de l'attente active juste après avec event.waitUntil
	clients.claim(); //permet de contrôler tout de suite la page sans attendre un rechargement (n'interceptera pas les fetch avant un deuxième chargement sinon par exemple)
	try
	{
		event.waitUntil(delete_older_caches());
	}
	catch (e)
	{
		console.error(e);
	}
}


self.addEventListener("activate", when_activate);

//POUR ARCHIVE : le code ci-dessous est l'ancien fonctionnement de l'activation, avant changement de syntaxe de then à async
/*
 self.addEventListener("activate", event => {
 console.log("Service Worker activating...");
 clients.claim();//permet de contrôler tout de suite la page sans attendre un rechargement (n'interceptera pas les fetch avant un deuxième chargement sinon par exemple)

 // delete any unexpected caches
 event.waitUntil(
 caches
 .keys()
 .then(keys => keys.filter(key => key !== CACHE_VERSION))
 .then(keys =>
 Promise.all(
 keys.map(key => {
 console.log(`Deleting cache ${key}`);
 return caches.delete(key);
 })
 )
 )
 );
 });
 */

//fonction qui, dans cette appli, ne sera presque jamais appelée.... car on précache tout. Mais on ne sait jamais.
async function cache_request(request, response)
{
	if (response.type !== "error" && response.type !== "opaque")
	{//on ne cache pas les erreurs réseau
		try
		{
			console.log(`SW:caching url:${request.url}`);
			const currentCache = await caches.open(CACHE_VERSION);
			await currentCache.put(request, response.clone());
		}
		catch (e)
		{
			console.error(e);
		}
	}
}

async function fetch_response(req)
{
	try
	{
		let response = await caches.match(req);//on attend d'avoir la réponse pour progresser, sans attente active

		if (!response)
		{//la réponse est vide : le cache ne contient pas la valeur recherchée : on va donc appeler le réseau
			console.log(`SW:url:${req.url} not in cache : fetching through network`);
			response = await fetch(req);//on fetch, sans attente active
			await cache_request(req, response);//CRUCIAL : sans cela on passe à la suite et la réponse est returned, donc traitée AVANT la mise en cache (car cache_request est async! Le flot continue donc pendant ses propres await) : qui ne peut donc se faire car la réponse a déjà été consommée
		}
		else
		{
			console.log(`SW:url:${req.url} found in cache`);
		}
		return response;
	}
	catch (e)
	{
		console.error(e);
	}
}

function when_fetch(event)
{
	{
		let req = event.request;
		console.log(`SW:fetching url:${req.url}`);
		if (req.url.includes("?"))//TODO étendre ce test à brython et sa lib aussi... enfin à tout ce qui possède un "?" au milieu en fait et tester
				//ATTENTION!!!!!!!!!!!!!! L'appel à Brython.js semble être en lien avec le web worker : à surveiller?
				{//cas particulier de brython qui appelle ses scripts en les postfixant d'un numéro, on le strippe avant de fetcher pour obtenir le vrai nom de fichier
					console.log("SW:stripping url of parameters");
					const newUrl = event.request.url.split('?')[0];
					req = new Request(newUrl, event.request);
				}

		// Cache-First Strategy : si l'appli est mise à jour, il faudra mettre à jour la version du service worker pour qu'il re-précache. Comme l'appli n'a pas BESOIN d'assets réseau (pas de données) c'est plus efficient car ça évite des fetch réseau inutiles
		//à noter que pour une appli échangeant effectivement des données il vaudrait mieux une stratégie network first VOIRE différencier entre pages et objets json, de façon hybride : début de piste par ici https://pwa-workshop.js.org/fr/4-api-cache/#cache-update-refresh
		response = fetch_response(req);
		event.respondWith(response);
	}
}

self.addEventListener("fetch", when_fetch);


//POUR ARCHIVE : ancien code de fetch, en syntaxe then et pas async
/*self.addEventListener("fetch", event => {
 console.log(`FETCH URL : ${event.request.url}`);
 let req = event.request;
 if (event.request.url.includes("main.bry"))
 {
 console.log("bry détecté");
 const newUrl = event.request.url.split('?')[0];
 console.log(newUrl);

 req = new Request(newUrl, event.request);
 }
 console.log(`NEW URL : ${req.url}`);
 // Cache-First Strategy
 event.respondWith(
 caches
 .match(req) // check if the request has already been cached
 .then(cached => cached || fetch(req)) // otherwise request network
 .then(
 response =>
 cache(req, response) // put response in cache
 .then(() => response) // resolve promise with the network response
 )
 );
 });

 function cache(request, response) {
 if (response.type === "error" || response.type === "opaque") {
 return Promise.resolve(); // do not put in cache network errors
 }

 return caches
 .open(CACHE_VERSION)
 .then(cache => cache.put(request, response.clone()));
 }
 */




//POUR ARCHIVE : ci-dessous un brouillon de stratégie network-first, ne marchant pas très bien (du fait du problème du 'NAVIGATE' ; pourrait être réglé en différenciant plutôt le format des url (entre une page et un JSON pour une stratégie de cache hybride)
/*self.addEventListener("fetch", event => {
 console.log(`event request : ${event.request}`);

 if (event.request.mode === 'navigate')//il s'agit d'une requêtre liée à la navigation de l'utilisateur sur le domaine du site : ATTENTION, dans les tests ça ne marchait PAS car le browser n'utilisait pas navigate pour les pages
 {
 console.log("NAVIGATE");
 event.respondWith((async() => {
 try {
 const preloadResponse = await event.preloadResponse;//on récupère la réponse préchargée de la reauête
 if (preloadResponse)//il y avait moyen de précharger la réponse
 {
 console.log("PRECHARGE");
 return preloadResponse;//on renvoie alors la réponse prechargee
 }
 //pourri : il vaudrait mieux factoriser les return
 console.log("FETCH");//pourri: les console.log de cette fonction sont horribles
 return await fetch(event.request);//il n'y avait pas de réponse préchargée, alors on passe le fetch au serveur en espérant qu'il y ait du réseau
 } catch (e)//pas moyen de récupérer une réponse
 {
 console.log("CACHE");
 const currentCache = await caches.open(CACHE_VERSION);
 return await currentCache.match(event.request);
 }
 })());
 }


 });
 */
