# Ostatic

Extra-simple static file server that checks JWT token against Auth API.


## Usage

```
docker run -d -e OSTATIC_BACKEND_ROUTE=http://localhost:8000/auth -v $PWD/static:/app/static -p 8000:80 matthieugouel/ostatic
```