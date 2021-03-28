# Ostatic

Extra-simple static file server that checks JWT token against Auth API and delivers short-lived token to access static resources.


## Usage

```
docker run -d -e OSTATIC_BACKEND_ROUTE=http://localhost:8001/auth -v $PWD/static:/app/static -p 8000:80 matthieugouel/ostatic
```

### Get Token

```
curl -H 'Authorization: {{ BACKEND_TOKEN }}' http://127.0.0.1:8000/token
```
```
{"access_token": {{ SHORT_LIVED_TOKEN }},
"token_type":"bearer"}%
```

### Access to a static resource

```
curl http://127.0.0.1:8000/static/hello.txt?token={{ SHORT_LIVED_TOKEN }}
