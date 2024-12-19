import aiohttp
from aiohttp import web
import tomllib
import subprocess
import asyncio
import psutil

class Runner:
    def __init__(self, name, args):
        self.name = name
        self.port = args.get("port", 8080)
        self.host = args.get("host", "localhost")
        self.loop = asyncio.get_running_loop()

        binary = args.pop("exec", "llama-server")
        if isinstance(binary, str):
            cmd = [binary]
        else:
            cmd = binary
        for k, v in args.items():
            if v == True:
                cmd.append("--"+k)
            else:
                cmd.extend(["--"+k, str(v)])
        self.proc = subprocess.Popen(cmd)

        self.keepalive()
        self._timeout()
    
    def _timeout(self):
        if self.stop_at < self.loop.time():
            self.terminate()
        else:
            self.timer = self.loop.call_at(self.stop_at, self._timeout)
    
    def keepalive(self):
        global timeout
        self.stop_at = self.loop.time()+timeout

    def terminate(self):
        self.timer.cancel()
        print("stopping runner for", self.name)
        self.proc.terminate()
    
    async def online(self):
        while True:
            if self.proc.poll() != None:
                return False
            ps = psutil.Process(self.proc.pid)
            conn = ps.net_connections()
            print(conn)
            for sock in  conn:
                if sock.laddr.port == self.port:
                    return True
            await asyncio.sleep(1)


active_runner = None

async def forward_request(request):
    global active_runner
    model = (await request.json())["model"]
    print(active_runner)
    if active_runner == None or active_runner.name != model or not await active_runner.online():
        if active_runner != None:
            active_runner.terminate()
        active_runner = Runner(model, runners[model])
        await active_runner.online()
    active_runner.keepalive()

    target_url = f"http://{active_runner.host}:{active_runner.port}/v1/{request.match_info['tail']}"
    print(target_url)

    async with aiohttp.ClientSession() as session:
        async with session.request(method=request.method,
                                   url=target_url,
                                   headers=request.headers,
                                   data=await request.read()) as req:

            resp = web.StreamResponse(status=req.status, reason=req.reason)
            resp.headers.update(resp.headers)
            await resp.prepare(request)
            async for chunk in req.content.iter_any():
                await resp.write(chunk)
            await resp.write_eof()
            return resp

async def models_request(request):
    #TODO fill in model details
    return web.json_response(
        {"object":"list",
         "data":[{"id":k,"object":"model"} for k in runners.keys()]}
    )


async def index_handler(request):
    return web.Response(text="Ollama is running", status=200)

async def tags_list_handler(request):
    # TODO: Implement logic for listing tags
    return web.json_response({"message": "ListHandler not implemented yet"})

async def version_handler(request):
    # Import the version module or define it as needed
    version = {"version": "1.0"}  # Example version dictionary
    return web.json_response(version)

async def pull_handler(request):
    # TODO: Implement logic for generating something
    return web.json_response({"message": "Generate operation not implemented yet"})

async def generate_handler(request):
    # TODO: Implement logic for generating something
    return web.json_response({"message": "Generate operation not implemented yet"})

async def chat_handler(request):
    # TODO: Implement logic for chat interaction
    return web.json_response({"message": "Chat operation not implemented yet"})

async def embed_handler(request):
    # TODO: Implement logic for embedding
    return web.json_response({"message": "Embed operation not implemented yet"})

async def embeddings_handler(request):
    # TODO: Implement logic for embeddings
    return web.json_response({"message": "Embeddings operation not implemented yet"})

async def create_handler(request):
    # TODO: Implement logic for creating something
    return web.json_response({"message": "Create operation not implemented yet"})

async def push_handler(request):
    # TODO: Implement logic for pushing data
    return web.json_response({"message": "Push operation not implemented yet"})

async def copy_handler(request):
    # TODO: Implement logic for copying data
    return web.json_response({"message": "Copy operation not implemented yet"})

async def delete_handler(request):
    # TODO: Implement logic for deleting something
    return web.json_response({"message": "Delete operation not implemented yet"})

async def show_handler(request):
    # TODO: Implement logic for showing something
    return web.json_response({"message": "Show operation not implemented yet"})

async def create_blob_handler(request):
    digest = request.match_info['digest']
    # TODO: Implement logic for creating a blob with given digest
    return web.json_response({"message": f"CreateBlobHandler for {digest} not implemented yet"})

async def head_blob_handler(request):
    digest = request.match_info['digest']
    # TODO: Implement logic for getting headers of the blob with given digest
    return web.json_response({"message": f"HeadBlobHandler for {digest} not implemented yet"})

async def ps_handler(request):
    # TODO: Implement logic for showing processes
    return web.json_response({"message": "PsHandler not implemented yet"})

routes = [
    web.route('GET', '/v1/models', models_request),
    web.route('*', '/v1/{tail:.*}', forward_request),

    # Ollama compat
    web.get('/', index_handler),
    web.head('/', index_handler),
    web.get('/api/tags', tags_list_handler),
    web.get('/api/version', version_handler),
    web.post('/api/pull', pull_handler),
    web.post('/api/generate', generate_handler),
    web.post('/api/chat', chat_handler),
    web.post('/api/embed', embed_handler),
    web.post('/api/embeddings', embeddings_handler),
    web.post('/api/create', create_handler),
    web.post('/api/push', push_handler),
    web.post('/api/copy', copy_handler),
    web.delete('/api/delete', delete_handler),
    web.post('/api/show', show_handler),
    web.post('/api/blobs/{digest}', create_blob_handler),
    web.head('/api/blobs/{digest}', head_blob_handler),
    web.get('/api/ps', ps_handler)
]

app = web.Application()
app.add_routes(routes)

with open("runners.toml", "rb") as f:
    runners = tomllib.load(f)

timeout = runners.pop("timeout", 5*60)

web.run_app(app, host='0.0.0.0', port=8765)
