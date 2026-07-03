from aiohttp import web

async def health_check(request):
    return web.Response(text="OK", status=200)

def run_web_server(port):
    app = web.Application()
    app.router.add_get('/health', health_check)
    web.run_app(app, port=port)
