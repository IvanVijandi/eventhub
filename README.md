# Eventhub

Aplicación web para venta de entradas utilizada en la cursada 2025 de Ingeniería y Calidad de Software. UTN-FRLP

## Dependencias

-   python 3
-   Django
-   sqlite
-   playwright
-   ruff

## Instalar dependencias

`pip install -r requirements.txt`

## Iniciar la Base de Datos

`python manage.py migrate`

### Crear usuario admin

`python manage.py createsuperuser`

### Llenar la base de datos

`python manage.py loaddata fixtures/events.json`

### Sembrar datos en la base de datos

`python seed.py`

## Iniciar app

`python manage.py runserver`

## Integrantes

`Ivan Andres Vijandi`
`Gastón Ferraris Davies`
`Pietrantuono Franco`
`Moscuzza Vicente`
`Nicolas Valdes`
`Valentino Siadore`
