FROM python:alpine3.17

STOPSIGNAL SIGINT

RUN echo "Running port is set to: 8000"

RUN mkdir /app

COPY * /app
WORKDIR /app

RUN echo "Installing necessary modules"

RUN yes | python -m pip install -r requirements.txt

EXPOSE 8000/tcp

CMD uvicorn main:app --host 0.0.0.0 --port 8000