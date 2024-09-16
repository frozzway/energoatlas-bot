import uvicorn


uvicorn.run(
    'stub_server:app',
    host='0.0.0.0',
    port=8888,
    reload=True,
)
