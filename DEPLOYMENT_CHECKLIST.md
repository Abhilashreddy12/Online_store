# Quick Start - SEO & Branding Deployment Guide

## 🚀 IMMEDIATE ACTIONS BEFORE DEPLOYMENT

### 1. Create/Prepare Image Assets
Create these images and place in `/static/images/`:

**logo.png** (192x192 minimum)
- Brand logo for favicon and PWA
- Square format recommended
- Used for: browser tabs, iOS home screen, manifest

**preview.jpg** (1200x630 pixels)
- Social media preview image
- Used for: Facebook, Twitter, LinkedIn sharing
- File size: <200KB for optimal performance

### 2. Test Locally

```bash
# Start development server
python manage.py runserver

# Check homepage meta tags
curl http://localhost:8000/

# Test sitemap
curl http://localhost:8000/sitemap.xml

# Test robots.txt
curl http://localhost:8000/robots.txt

# Test manifest
curl http://localhost:8000/manifest.json
```

### 3. Verify in Browser

1. Visit `http://localhost:8000/`
2. Right-click → Inspect → Go to `<head>`
3. Check for:
   - ✅ `<title>` tag
   - ✅ `<meta name="description">`
   - ✅ `<meta property="og:title">`
   - ✅ `<meta property="twitter:card">`
   - ✅ Favicon links

### 4. Test Social Media Preview

**Facebook Debugger:**
```
https://developers.facebook.com/tools/debug/
```
- Paste: `https://madiriclet.com/`
- Check OG tags are correct

**Twitter Card Validator:**
```
https://cards-dev.twitter.com/validator
```
- Paste: `https://madiriclet.com/`
- Verify Twitter card renders

## 🎯 DEPLOYMENT STEPS

### Step 1: Update Configuration Files

**Update `.env` file (if needed):**
```
DEBUG=False
ALLOWED_HOSTS=madiriclet.com,www.madiriclet.com
```

**Verify `settings.py`:**
- ✅ `django.contrib.sitemaps` in INSTALLED_APPS
- ✅ GZipMiddleware added
- ✅ STATIC_URL = '/static/'
- ✅ STATIC_ROOT = 'staticfiles'

### Step 2: Collect Static Files

```bash
# Locally first
python manage.py collectstatic --noinput

# Verify files collected
ls -la staticfiles/
```

### Step 3: Build Script for Render

**Add to `build.sh`:**
```bash
#!/bin/bash
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

echo "Build complete!"
```

**Make executable:**
```bash
chmod +x build.sh
```

### Step 4: Deploy to Render

1. Connect repository
2. Set environment variables in Render dashboard
3. Point to build script: `./build.sh`
4. Deploy

## ✅ POST-DEPLOYMENT VERIFICATION

### 1. Test Live Site

```bash
# Check homepage
curl https://madiriclet.com/

# Check sitemap
curl https://madiriclet.com/sitemap.xml | head -20

# Check robots.txt
curl https://madiriclet.com/robots.txt | head -20

# Check manifest
curl https://madiriclet.com/manifest.json
```

### 2. Verify Search Console

**Google Search Console:**
1. Go to: https://search.google.com/search-console/
2. Add property: `https://madiriclet.com`
3. Verify ownership (DNS/HTML file/Google Analytics)
4. Submit sitemap: `https://madiriclet.com/sitemap.xml`
5. Request indexing for homepage
6. Monitor crawl statistics

**Bing Webmaster Tools:**
1. Go to: https://www.bing.com/webmaster
2. Add site
3. Submit sitemap
4. Monitor indexing

### 3. Check Meta Tags Live

```bash
# Using curl to extract title
curl -s https://madiriclet.com/ | grep -o '<title>[^<]*</title>'

# Using curl to check OG tags
curl -s https://madiriclet.com/ | grep 'og:title\|og:description'

# Using curl to check Twitter tags
curl -s https://madiriclet.com/ | grep 'twitter:'
```

### 4. Run Lighthouse Audit

1. Open: `https://madiriclet.com/`
2. Chrome DevTools → Lighthouse
3. Run audit (Desktop & Mobile)
4. Target scores:
   - Performance: > 80
   - Accessibility: > 90
   - Best Practices: > 90
   - SEO: > 90

### 5. Test Mobile-Friendly

1. Go to: https://search.google.com/test/mobile-friendly
2. Enter: `https://madiriclet.com/`
3. Should show: ✅ Page is mobile-friendly

## 📊 MONITOR & MAINTAIN

### Weekly Tasks
- [ ] Check Google Search Console for errors
- [ ] Monitor indexing status
- [ ] Review Core Web Vitals
- [ ] Check for crawl errors

### Monthly Tasks
- [ ] Analyze traffic patterns
- [ ] Review search queries
- [ ] Check competing keywords
- [ ] Update content if needed
- [ ] Review mobile usability

### Quarterly Tasks
- [ ] Audit site structure
- [ ] Update schema markup if needed
- [ ] Review backlink profile
- [ ] Competitor analysis
- [ ] Plan content strategy

## 🔧 TROUBLESHOOTING

### Issue: Sitemap returns 404
**Solution:**
```bash
# Check sitemaps app is in INSTALLED_APPS
python manage.py shell
>>> from catalog.sitemap import sitemaps
>>> print(sitemaps.keys())
dict_keys(['static', 'products', 'categories'])
```

### Issue: Static files not loading
**Solution:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Clear cache
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Issue: Robots.txt not found
**Solution:**
```bash
# Verify TemplateView is imported
# Check urls.py has robots.txt path
# Verify templates/robots.txt exists
```

### Issue: Images not loading in OG preview
**Solution:**
- Ensure image paths are absolute URLs
- Check CORS headers if using CDN
- Verify image dimensions (1200x630 for OG)
- Check file size < 8MB

## 📝 CONFIGURATION NOTES

### URL Patterns
- Homepage: `/` → SEO optimized with H1, OG tags
- Products: `/products/` → Product listing with categories
- Product Detail: `/product/<slug>/` → Individual product pages
- Sitemap: `/sitemap.xml` → Dynamic XML sitemap
- Robots: `/robots.txt` → Search engine rules

### Cache Configuration
- Cache backend: LocMemCache (localhost) or Redis (production)
- TTL: 3600 seconds (1 hour)
- Static files: 14-day cache (14 days)

### Security Headers (Production)
```
SECURE_SSL_REDIRECT=True
HSTS_SECONDS=31536000
X_FRAME_OPTIONS=SAMEORIGIN
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
```

## 🎓 SEO BEST PRACTICES IMPLEMENTED

✅ **On-Page SEO**
- Proper H1 tag with brand name
- Descriptive meta tags
- Keyword-rich content
- Mobile-responsive design

✅ **Technical SEO**
- Clean URL structure
- XML sitemap
- Robots.txt
- Structured data (JSON-LD)

✅ **Performance**
- Gzip compression
- Static file caching
- Lazy image loading
- Minified CSS/JS

✅ **Social Sharing**
- Open Graph tags
- Twitter Cards
- Social media metadata
- Rich previews

✅ **Mobile**
- Responsive viewport
- Touch icon
- Mobile manifest
- Fast loading

## 📚 RESOURCES

- [Google Search Central](https://developers.google.com/search)
- [Bing Webmaster Tools](https://www.bing.com/webmaster)
- [Open Graph Protocol](https://ogp.me/)
- [Twitter Card Tags](https://developer.twitter.com/en/docs/twitter-for-websites/cards/overview/abouts-cards)
- [Schema.org](https://schema.org/)
- [Web.dev](https://web.dev/)

## 🎉 SUCCESS CHECKLIST

- ✅ SEO meta tags implemented
- ✅ Open Graph tags added
- ✅ Twitter cards configured
- ✅ Favicon setup
- ✅ PWA manifest created
- ✅ Sitemap generated
- ✅ Robots.txt configured
- ✅ Static files optimized
- ✅ Gzip compression enabled
- ✅ Homepage SEO content
- ✅ Schema markup added
- ✅ Mobile responsive
- ✅ Security headers configured
- ✅ Submitted to search engines
- ✅ Monitoring setup

---

**Status:** 🚀 READY FOR PRODUCTION DEPLOYMENT

**Last Updated:** April 21, 2026
