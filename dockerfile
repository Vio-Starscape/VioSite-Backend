FROM python:3.10-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git

COPY ./requirements.txt /app
RUN pip3 install -r requirements.txt

ENV PORT=5567

COPY . /app

EXPOSE ${PORT}

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
