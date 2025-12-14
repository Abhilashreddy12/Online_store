## 🔧 Render Configuration Checklist

### Build Command (in Settings):
```bash
./build.sh
```

OR if that doesn't work:
```bash
pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate --no-input
```

### Start Command (in Settings):
```bash
gunicorn shopping_store.wsgi:application
```

### Environment Variables (Required):
```
DATABASE_URL=postgresql://clothing_store_77x2_user:4n37tpIdUyEx1dpcGZEfe8CFvjy81mYV@dpg-d4ui897pm1nc73b5q650-a/clothing_store_77x2
SECRET_KEY=inwu$&yh!4)ylc%viq7=4yi6dsf*stvu5b5hezs_$q3qw&i)_h
DEBUG=False
```

### If migrations still don't run:

The build.sh file might not have execute permissions. Try updating Build Command to:
```bash
bash build.sh
```

This will work without needing chmod.
