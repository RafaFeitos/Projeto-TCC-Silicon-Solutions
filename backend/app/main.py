from fastapi import FastAPI


app = FastAPI(
    title="Industrial Monitor API",
    description="API para monitoramento de máquinas industriais legadas.",
    version="0.1.0",
)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "industrial-monitor",
    }