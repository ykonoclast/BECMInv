
const CACHE_NAME = "V2";//TODO changer ces noms pas terribles
const STATIC_CACHE_URLS = ["/", "favicon.ico", "css/styles.css", "python/main.bry", "js/brython.js", "js/brython_stdlib.js", "icons/logo.png", "icons/logo192.png", "icons/logo512.png", "fonts/EBGaramond-Italic.otf", "fonts/EBGaramond-Regular.otf", "fonts/EBGaramond-SemiBold.otf"];
//TODO COMMENTER PARTOUT!!!!!
//PREFIXER CHAQUE LOG PAR LE PREFIX "cache_name" (a changer)

async function pre_cache()
{
	try {
		console.log("Opening cache...");//todo indiquer version, de manière générale voir pour logging de bonne qualité
		const lecache = await caches.open(CACHE_NAME);
		lecache.addAll(STATIC_CACHE_URLS);
	} catch (e)
	{
		console.error(e);
	}
}

function when_install(event)
{
	self.skipWaiting();
	console.log("Service Worker installing...");
	try {
		event.waitUntil(pre_cache());
	} catch (e)
	{
		console.error(e);
	}
}

self.addEventListener("install", when_install);


self.addEventListener("activate", event => {
	console.log("Service Worker activating...");
	clients.claim();//permet de contrôler tout de suite la page sans attendre un rechargement (n'interceptera pas les fetch avant un deuxième chargement sinon par exemple)

	// delete any unexpected caches
	event.waitUntil(
			caches
			.keys()
			.then(keys => keys.filter(key => key !== CACHE_NAME))
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

/*
 self.addEventListener("fetch", event => {
 console.log(`event request url : ${event.request.url}`);
 event.respondWith(
 fetch(event.request)
 .catch(error => {
 console.log("FROM CACHE");
 return caches.match(event.request);
 })
 );
 });
 */

/*self.addEventListener("fetch", event => {
 console.log(`event request : ${event.request}`);

 if (event.request.mode === 'navigate')//il s'agit d'une requêtre liée à la navigation de l'utilisateur sur le domaine du site
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
 //TODO factoriser les return
 console.log("FETCH");//TODO les console.log de cette fonction sont horribles
 return await fetch(event.request);//il n'y avait pas de réponse préchargée, alors on passe le fetch au serveur en espérant qu'il y ait du réseau
 } catch (e)//pas moyen de récupérer une réponse
 {
 console.log("CACHE");
 const lecache = await caches.open(CACHE_NAME);//TODO factoriser
 return await lecache.match(event.request);
 }
 })());
 }


 });
 */




//TODO commenter l'intégralité de cette merde et refactorer (mais pas dans ce sens là)
self.addEventListener("fetch", event => {
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
			.open(CACHE_NAME)
			.then(cache => cache.put(request, response.clone()));
}
