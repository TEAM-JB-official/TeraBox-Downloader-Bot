import asyncio
from aiohttp import web

async def health_check(request):
    return web.Response(text="OK", status=200)

async def run_web_server(port):
    """Start aiohttp web server on the given port within the current event loop."""
    app = web.Application()
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=port)
    await site.start()
    print(f"🌐 Web server running on port {port} (health check at /health)")

    # Keep the server alive until cancelled
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        await runner.cleanup()
        raise
