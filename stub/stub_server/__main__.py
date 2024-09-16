import uvicorn


uvicorn.run(
    'stub_server:app',
    host='localhost',
    port=8888,
    reload=True,
)
