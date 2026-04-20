# 🚀 Titan Mail Integration - Quick Start Checklist

## ✅ Step-by-Step Implementation

### Phase 1: Get Titan Mail Account (5 min)
- [ ] Go to https://www.titanmail.com/
- [ ] Sign up for Titan Mail
- [ ] Verify your domain
- [ ] Get SMTP credentials from dashboard
  - [ ] SMTP Host: `mail.titanmail.com`
  - [ ] SMTP Port: `587`
  - [ ] Email: `your-email@yourdomain.com`
  - [ ] Password: `your-password`

### Phase 2: Update Configuration (2 min)
- [ ] Open `.env` file in your project root
- [ ] Add/Update these variables:
  ```
  EMAIL_HOST=mail.titanmail.com
  EMAIL_PORT=587
  EMAIL_USE_TLS=True
  EMAIL_USE_SSL=False
  EMAIL_HOST_USER=your-email@yourdomain.com
  EMAIL_HOST_PASSWORD=your-password
  DEFAULT_FROM_EMAIL=your-email@yourdomain.com
  SERVER_EMAIL=your-email@yourdomain.com
  USE_CONSOLE_EMAIL=False
  ```
- [ ] Save `.env` file
- [ ] Verify `.env` is in `.gitignore` (never commit secrets!)

### Phase 3: Install/Update Dependencies (1 min)
- [ ] All required packages already included
- [ ] No additional pip installs needed

### Phase 4: Restart Django (2 min)
- [ ] Stop Django development server (Ctrl+C)
- [ ] Run: `python manage.py runserver`
- [ ] Django will load the new email configuration automatically

### Phase 5: Test Email Sending (3 min) ⚡
```bash
# Option A: Test in Django Shell
python manage.py shell

# Then run:
from django.core.mail import send_mail
result = send_mail(
    'Test Subject',
    'Test email body',
    'your-email@yourdomain.com',
    ['recipient@example.com'],
)
print("✅ Email sent!" if result else "❌ Failed to send")
```

```bash
# Option B: Test with Real Order
# Place a test order in your store
# Check your email - you should receive order confirmation
```

### Phase 6: Verify Email Flow (5 min)
- [ ] **Test Order Confirmation**: Place a test order → Check email for confirmation
- [ ] **Test Welcome Email**: Register new account → Check email for welcome
- [ ] **Test Password Reset**: Request password reset → Check email for reset link
- [ ] **Check Order Details**: Login → View order → See confirmation was sent

### Phase 7: Production Deployment (3 min)
If deploying to Heroku/Render:
- [ ] Add environment variables in hosting dashboard:
  - [ ] EMAIL_HOST=mail.titanmail.com
  - [ ] EMAIL_PORT=587
  - [ ] EMAIL_USE_TLS=True
  - [ ] EMAIL_USE_SSL=False
  - [ ] EMAIL_HOST_USER=your-titanmail@yourdomain.com
  - [ ] EMAIL_HOST_PASSWORD=your-password
  - [ ] DEFAULT_FROM_EMAIL=your-titanmail@yourdomain.com
  - [ ] SERVER_EMAIL=your-titanmail@yourdomain.com
- [ ] Deploy application
- [ ] Test email sending on production
- [ ] Monitor email delivery

---

## 📊 What Was Set Up For You

### ✅ Email Services Created
- `orders/email_service.py` - Complete email sending service
- `customers/email_service.py` - Customer email utilities (imported in above)

### ✅ Email Templates Created (12 files)
- Order confirmation (HTML + Text)
- Invoice email (HTML + Text)
- Payment received (HTML + Text)
- Order status updates (HTML + Text)
- Welcome email (HTML + Text)
- Password reset (Django built-in)

### ✅ Automatic Email Triggers
- Order confirmation → Sent when order created
- Payment confirmation → Sent when payment received
- Welcome email → Sent when user registers
- Password reset → Django built-in (already working)

### ✅ Configuration Updated
- `settings.py` - Titan Mail SMTP configured
- `.env.example` - Template with Titan Mail settings
- Signal handlers - Auto-email triggering

---

## 🧪 Testing Scenarios

### Scenario 1: Order Confirmation
```
1. Go to Store
2. Add item to cart
3. Checkout
4. Place order
✅ Should receive order confirmation email
```

### Scenario 2: Welcome Email
```
1. Click Register
2. Create account with email
3. Submit form
✅ Should receive welcome email immediately
```

### Scenario 3: Password Reset
```
1. Click "Forgot Password"
2. Enter email
3. Submit form
✅ Should receive password reset link email
```

### Scenario 4: Invoice Download
```
1. Place order
2. Go to orders page
3. Download invoice
✅ Invoice PDF available for download
```

---

## 🔍 How to Check If It's Working

### Check 1: Email Backend
```python
python manage.py shell
from django.conf import settings
print(settings.EMAIL_HOST)
print(settings.EMAIL_PORT)
print(settings.DEFAULT_FROM_EMAIL)
```

### Check 2: Email Logs
```bash
# Django logs
python manage.py runserver  # Check console output for email logs
```

### Check 3: Test Email
```bash
# Send test email
python manage.py shell

from django.core.mail import send_mail
send_mail(
    'Test',
    'This is a test',
    'from-email@yourdomain.com',
    ['to-email@example.com'],
)
```

### Check 4: Real Test in Site
1. Register new account → Check email for welcome
2. Place order → Check email for confirmation
3. Click forgot password → Check email for reset

---

## ⚠️ Common Issues & Solutions

### Issue: "No module named 'orders.email_service'"
**Solution**: 
- Make sure you have the latest code
- Run: `python manage.py migrate`
- Restart Django server

### Issue: "Connection refused" or timeout
**Solution**:
- Check your internet connection
- Verify EMAIL_HOST is correct: `mail.titanmail.com`
- Verify EMAIL_PORT is correct: `587`
- Check credentials in .env file

### Issue: Emails going to spam
**Solution**:
- Add SPF record to your domain
- Add DKIM signature
- Use your domain email (not generic)
- Check Titan Mail documentation for SPF/DKIM setup

### Issue: "Authentication failed"
**Solution**:
- Verify Titan Mail credentials
- Check .env file has correct values
- Make sure no extra spaces in credentials
- Verify domain is verified in Titan Mail

### Issue: No email received
**Solution**:
- Check recipient email is correct
- Check spam/junk folder
- Use console backend to debug: `USE_CONSOLE_EMAIL=True`
- Check Django logs for errors

---

## 📚 Documentation Files Created

1. **TITAN_MAIL_SETUP.md** - Complete setup guide with examples
2. **TITAN_MAIL_INTEGRATION_COMPLETE.md** - Summary of implementation
3. **This file** - Quick start checklist

---

## 🎯 Next Steps

1. ✅ Get Titan Mail account
2. ✅ Update .env with credentials
3. ✅ Restart Django
4. ✅ Test email sending
5. ✅ Customize email templates (optional)
6. ✅ Deploy to production

---

## 💡 Tips & Tricks

### Tip 1: Customize Email Templates
Edit HTML templates in `templates/orders/emails/` to add:
- Your logo
- Brand colors
- Custom messages
- Social media links

### Tip 2: Manual Email Sending
```python
from orders.email_service import OrderEmailService
order = Order.objects.get(id=1)
OrderEmailService.send_order_confirmation(order)
```

### Tip 3: Test Without Sending
```bash
# Use console backend to print instead of send
USE_CONSOLE_EMAIL=True
python manage.py runserver
# Emails will print to terminal instead
```

### Tip 4: Monitor Email Delivery
Keep email logs to track:
- Emails sent successfully
- Failed deliveries
- Customer engagement

---

## 🔐 Security Reminders

✅ **Never:**
- Commit .env file to git
- Hardcode credentials in code
- Send credentials via email
- Share credentials publicly

✅ **Always:**
- Use environment variables
- Keep .env in .gitignore
- Use TLS encryption (port 587)
- Monitor email delivery
- Update credentials if compromised

---

## 📞 Need Help?

- **Titan Mail Support**: https://www.titanmail.com/
- **Django Documentation**: https://docs.djangoproject.com/
- **Setup Guide**: Read `TITAN_MAIL_SETUP.md`
- **Implementation Details**: Read `TITAN_MAIL_INTEGRATION_COMPLETE.md`

---

## ✨ Features Now Available

✅ Automatic order confirmation emails
✅ Automatic welcome emails for new customers  
✅ Automatic payment confirmation emails
✅ Invoice emails with PDF attachment
✅ Order status update notifications
✅ Password reset emails
✅ Professional HTML email templates
✅ Plain text email fallback
✅ Complete error handling & logging
✅ Security best practices implemented

---

**Status**: 🟢 **Ready to Configure**

Follow the checklist above to get started! 🚀
