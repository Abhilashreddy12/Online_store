# 🚀 Render Deployment Guide - Clothing Store

## ✅ Files Updated for Deployment

All necessary files have been created and configured:
- ✅ [`shopping_store/requirements.txt`](shopping_store/requirements.txt ) - Added dj-database-url
- ✅ [`shopping_store/shopping_store/settings.py`](shopping_store/shopping_store/settings.py ) - Production-ready with DATABASE_URL support
- ✅ build.sh - Build script for Render
- ✅ runtime.txt - Python 3.13.2
- ✅ .gitignore - Exclude sensitive files
- ✅ .env - Local development variables
- ✅ .env.example - Template for environment variables

---

## 📋 Step-by-Step Deployment to Render

### **1. Prepare Git Repository**

```powershell
# Make sure you're in the project directory
cd A:\online_store\shopping_store

# Add all files
git add .

# Commit changes
git commit -m "Configure for Render deployment with PostgreSQL"

# Push to GitHub (you already did this)
git push origin master
```

---

### **2. Configure Render Web Service**

Go to https://render.com/dashboard

#### **Create New Web Service:**
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure as follows:

**Basic Settings:**
- **Name:** `clothing-store` (or your preferred name)
- **Region:** Oregon (US West) - Same as your database
- **Branch:** `master`
- **Root Directory:** (leave blank)
- **Runtime:** Python 3

**Build & Deploy:**
- **Build Command:** `chmod +x build.sh && ./build.sh`
- **Start Command:** `gunicorn shopping_store.wsgi:application --bind 0.0.0.0:$PORT`

**Instance Type:**
- Free (or paid for production)

---

### **3. Set Environment Variables in Render**

In your Web Service dashboard, go to **"Environment"** tab and add:

```
SECRET_KEY=inwu$&yh!4)ylc%viq7=4yi6dsf*stvu5b5hezs_$q3qw&i)_h
DEBUG=False
DATABASE_URL=postgresql://clothing_store_77x2_user:4n37tpIdUyEx1dpcGZEfe8CFvjy81mYV@dpg-d4ui897pm1nc73b5q650-a/clothing_store_77x2
ALLOWED_HOSTS=.onrender.com
PYTHON_VERSION=3.13.2
```

**Important Notes:**
- The `DATABASE_URL` is your **Internal Database URL** from Render PostgreSQL
- Keep `DEBUG=False` in production
- After deployment, add your specific domain: `ALLOWED_HOSTS=your-app-name.onrender.com,.onrender.com`

---

### **4. Deploy!**

Click **"Create Web Service"**

Render will:
1. ✅ Clone your repository
2. ✅ Install Python 3.13.2
3. ✅ Run `build.sh` (install packages, collectstatic, migrate)
4. ✅ Start gunicorn server
5. ✅ Assign you a URL: `https://your-app-name.onrender.com`

**First deployment takes 5-10 minutes.**

---

### **5. Create Superuser**

After successful deployment:

1. Go to Render Dashboard → Your Web Service
2. Click **"Shell"** tab
3. Run:
```bash
python manage.py createsuperuser
```

Follow prompts to create admin user.

---

### **6. Access Your Application**

- **Frontend:** `https://your-app-name.onrender.com/`
- **Admin:** `https://your-app-name.onrender.com/admin/`
- **Dashboard:** `https://your-app-name.onrender.com/dashboard/`

---

## 🔧 How It Works

### **Local Development (Your Computer):**
```python
# settings.py detects NO DATABASE_URL in .env
# Uses local PostgreSQL:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'clothing_store',
        'USER': 'postgres',
        'PASSWORD': 'abhi',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### **Production (Render):**
```python
# settings.py detects DATABASE_URL environment variable
# Uses Render PostgreSQL:
DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://clothing_store_77x2_user:4n37tp...@dpg-...a/clothing_store_77x2',
        conn_max_age=600,
        ssl_require=True
    )
}
```

---

## 🧪 Testing Locally Before Deployment

```powershell
# Make sure you're using local database
cd A:\online_store\shopping_store

# Activate virtual environment
A:/online_store/venv/Scripts/Activate.ps1

# Test with local settings
python manage.py runserver

# Visit: http://localhost:8000
```

---

## 🐛 Troubleshooting Common Errors

### **Error: "relation does not exist"**
**Solution:** Run migrations in Render Shell:
```bash
python manage.py migrate
```

### **Error: "ALLOWED_HOSTS"**
**Solution:** Add your Render domain to environment variables:
```
ALLOWED_HOSTS=your-app-name.onrender.com,.onrender.com
```

### **Error: "static files not found"**
**Solution:** Rebuild and run collectstatic:
```bash
python manage.py collectstatic --no-input
```

### **Error: "SSL connection required"**
**Solution:** Already fixed! `ssl_require=True` is set in [`shopping_store/shopping_store/settings.py`](shopping_store/shopping_store/settings.py )

---

## 📊 Database Credentials Reference

Your Render PostgreSQL Database:

```
Hostname: dpg-d4ui897pm1nc73b5q650-a
Port: 5432
Database: clothing_store_77x2
Username: clothing_store_77x2_user
Password: 4n37tpIdUyEx1dpcGZEfe8CFvjy81mYV

Internal URL (for Render apps):
postgresql://clothing_store_77x2_user:4n37tpIdUyEx1dpcGZEfe8CFvjy81mYV@dpg-d4ui897pm1nc73b5q650-a/clothing_store_77x2

External URL (for local connections):
postgresql://clothing_store_77x2_user:4n37tpIdUyEx1dpcGZEfe8CFvjy81mYV@dpg-d4ui897pm1nc73b5q650-a.oregon-postgres.render.com/clothing_store_77x2
```

---

## 🔐 Security Checklist

- [x] `.env` file excluded from git (in .gitignore)
- [x] `DEBUG=False` in production
- [x] `SECRET_KEY` in environment variables
- [x] `ALLOWED_HOSTS` properly configured
- [x] Whitenoise for static file serving
- [x] SSL/HTTPS enforced by Render
- [x] PostgreSQL with SSL connection

---

## 🎯 Post-Deployment Tasks

1. **Create Superuser** (see step 5)
2. **Add Products** via admin panel
3. **Create Banners** for promotions
4. **Test Checkout Flow**
5. **Configure Email** (future: SMTP settings)
6. **Set up Domain** (optional: custom domain)

---

## 📈 Monitoring

Render provides:
- **Logs:** Real-time application logs
- **Metrics:** CPU, Memory, Response times
- **Events:** Deployment history
- **Shell:** Direct access to running container

---

## 🔄 Updating Your Application

```powershell
# Make changes locally
# Test locally first!
python manage.py runserver

# Commit and push
git add .
git commit -m "Description of changes"
git push origin master

# Render auto-deploys from master branch!
```

---

## ✅ Success Indicators

Your deployment is successful when:
- ✅ Build completes without errors
- ✅ Migrations run successfully
- ✅ Admin panel accessible
- ✅ Static files load (CSS, images)
- ✅ Products display correctly
- ✅ Cart/checkout works
- ✅ Dashboard analytics visible

---

**Your app should now be live at:** `https://[your-service-name].onrender.com` 🎉

**Need help?** Check Render logs for detailed error messages.
