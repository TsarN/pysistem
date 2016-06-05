# PySistem

PySistem is contest management system written in Python 3, that uses Flask and SQLAlchemy

## Dependencies
 - Python 3.5 or higher
 - Flask
 - Flask-Babel
 - Flask-SQLAlchemy with backend (like MySQL)
 - SISTEM Backend (https://github.com/TsarN/sistem-backend)

## What database should I use?

MySQL is recommended, though any SQLAlchemy compatible database that supports multithreaded access is fine.

## How to deploy using Nginx and Gunicorn?
This guide is based on http://www.onurguzel.com/how-to-run-flask-applications-with-nginx-using-gunicorn/

### Requirements
 - Install pip for Python 3
 - Install Nginx
 - Install SISTEM-Backend (https://github.com/TsarN/sistem-backend)

Create a virtual enviroment for PySistem:

    $ virtualenv pysistem
    $ . pysistem/bin/activate

This will configure current terminal for virtual enviroment

### Installing PySistem
Install dependencies:

    $ pip install Flask Flask-Babel Flask-SQLAlchemy gunicorn

Simply copy `pysistem` folder from repository to newly created virtual enviroment

### Configuring Nginx
Check on your distro wiki for Nginx configuration manual

Create file `/etc/nginx/sites-available/pysistem.conf`:

```
server {
    listen 80;
    server_name pysistem.app;
 
    root /path/to/virtualenv/pysistem;
 
    access_log /path/to/virtualenv/logs/access.log;
    error_log /path/to/virtualenv/logs/error.log;
 
    location / {
        proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        if (!-f $request_filename) {
            proxy_pass http://127.0.0.1:8000;
            break;
        }
    }
}
```

Now, create logs folder and enable PySistem vhost:

    $ mkdir /path/to/virtualenv/logs
    # ln -s /etc/nginx/sites-available/pysistem.conf /etc/nginx/sites-enabled/

Check, if everything is OK:

    # nginx -t 

(Re)load Nginx:

    # /etc/init.d/nginx (re)start

### Post-installation configuration
If you want to use MySQL as your database backend, change `pysistem/conf.py`:
```python
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://user:password@localhost/db_name"
```

Also, make sure that you have pymysql installed:

    $ pip install pymysql
    
### Start PySistem
In your virtualhost terminal type

    $ gunicorn pysistem:app
    
Then, navigate to your application in browser and create admin account.
