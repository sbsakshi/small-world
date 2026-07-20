FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY . .
RUN uv pip install --system --no-cache -e . --group dev

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
