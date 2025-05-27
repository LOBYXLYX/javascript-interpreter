var js_code = 'onmessage = function(e) { postMessage("Hola desde el worker. Recibido: " + e.data + " desde " + e.origin);};'

var blob = window.Blob([js_code], {'type': 'application/javascript'})

var worker = window.Worker(blob)

console.log(worker)

worker.addEventListener('message', function (event){ 
    console.log(event)
})

worker.postMessage('Message', origin='https://miapp.local')


worker.terminate()