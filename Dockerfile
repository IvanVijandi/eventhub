# syntax=docker/dockerfile:1

# Ante cualquier duda visitar la guía de referencia de Dockerfile en
# https://docs.docker.com/go/dockerfile-reference/

ARG PYTHON_VERSION=3.12.6

FROM python:${PYTHON_VERSION}-slim AS base

# Evita que Python escriba archivos pyc.
ENV PYTHONDONTWRITEBYTECODE=1

# Evita que Python almacene en búfer stdout y stderr para evitar situaciones donde
# la aplicación falla sin emitir ningún registro debido al almacenamiento en búfer.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Descarga las dependencias como un paso separado para aprovechar el almacenamiento en caché de Docker.
# Utiliza un montaje de caché en /root/.cache/pip para acelerar construcciones posteriores.
# Utiliza un montaje de enlace a requirements.txt para evitar tener que copiarlos en esta capa.
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Copia el código fuente al contenedor.
COPY . .

RUN python3 manage.py makemigrations 
RUN python3 manage.py migrate 

##RUN chown 664 db.sqlite3
# Expone el puerto en el que la aplicación escucha.
EXPOSE 8000


# Ejecuta la aplicación.
CMD ["gunicorn", "eventhub.wsgi:application", "--bind", "0.0.0.0:8000"]