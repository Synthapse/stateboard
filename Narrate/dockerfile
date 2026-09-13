FROM python:3.9-slim

WORKDIR /raporting

COPY ./requirements.txt /raporting/requirements.txt

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --no-cache-dir --upgrade -r /raporting/requirements.txt && \
    apt-get remove -y build-essential && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /root/.cache

COPY . /raporting/

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "80"]