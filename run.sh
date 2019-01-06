nohup gunicorn -c gunicorn.conf manager:app >nohup.out 2>&1 &
