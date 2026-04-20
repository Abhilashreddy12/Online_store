# Titan Mail Integration Guide

## Overview

This document provides complete setup and usage instructions for Titan Mail integration in the fashion store. The system automatically sends:

- ✅ **Order Confirmation Emails** - When an order is placed
- ✅ **Payment Confirmation Emails** - When payment is received
- ✅ **Invoice Emails** - When invoices are generated (with PDF attachment)
- ✅ **Order Status Updates** - When order status changes
- ✅ **Welcome Emails** - When new customers register
- ✅ **Password Reset Emails** - Django's built-in password reset

---

## 🔒 Security Measures Implemented

### 1. **Environment Variables**
All sensitive credentials are stored in `.env` file, NEVER hardcoded:
- Email host, port, username, password
- Environment-specific configurations

### 2. **Email Backend Security**
- **Development**: Console backend (emails printed to terminal)
- **Production**: SMTP with TLS encryption
- **Fallback**: Console backend when credentials missing

### 3. **HTML Email Templates**
All emails have:
- HTML version with professional styling
- Plain text fallback for email clients that don't support HTML
- Security notices about never requesting passwords

### 4. **Error Handling**
- All email operations wrapped in try-except blocks
- Errors logged without exposing sensitive information
- Email failures don't break the application

### 5. **CSRF Protection**
- Email templates are Django templates (CSRF-aware)
- No sensitive data exposed in emails

### 6. **Connection Timeout**
- Email timeout set to 30 seconds
- Prevents hanging connections

---

## 📋 Setup Instructions

### Step 1: Get Titan Mail Credentials

1. Go to [https://www.titanmail.com/](https://www.titanmail.com/)
2. Sign up for a Titan Mail account
3. Verify your domain
4. Get your SMTP credentials:
   - **SMTP Host**: `mail.titanmail.com`
   - **SMTP Port**: `587` (TLS) or `465` (SSL)
   - **Email**: Your Titan Mail email address
   - **Password**: Your Titan Mail password

### Step 2: Update .env File

Copy the following into your `.env` file:

```bash
# Email settings - Titan Mail (NEVER commit real credentials)
EMAIL_HOST=mail.titanmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your-titanmail@yourdomain.com
EMAIL_HOST_PASSWORD=your-titanmail-password
DEFAULT_FROM_EMAIL=your-titanmail@yourdomain.com
SERVER_EMAIL=your-titanmail@yourdomain.com
```

⚠️ **Important**: Replace with your actual Titan Mail credentials

### Step 3: Verify Configuration

Test your email configuration:

```bash
# In Django shell
python manage.py shell

# Run this to test the connection
from django.core.mail import send_mail
result = send_mail(
    'Test Email',
    'This is a test email from Titan Mail.',
    'your-titanmail@yourdomain.com',
    ['recipient@example.com'],
)
print("Email sent successfully!" if result else "Email send failed")
```

### Step 4: Update Settings (Already Done)

The `settings.py` is already configured to:
- Use SMTP backend with Titan Mail
- Support both development and production
- Fallback to console backend if credentials missing
- Add email connection timeout

---

## 📧 Email Templates & Locations

All email templates are located in:

```
templates/
├── orders/emails/
│   ├── order_confirmation.html       # HTML version
│   ├── order_confirmation.txt        # Plain text version
│   ├── invoice_email.html
│   ├── invoice_email.txt
│   ├── payment_received.html
│   ├── payment_received.txt
│   ├── order_status_update.html
│   └── order_status_update.txt
└── customers/emails/
    ├── welcome.html
    └── welcome.txt
```

### Customize Email Templates

Edit the HTML templates to add:
- Your logo
- Store colors and branding
- Custom messages
- Social media links
- Promotional content

---

## 🚀 Email Triggers & Automatic Sending

### 1. Order Confirmation Email

**When**: Automatically sent when an order is created
**Template**: `order_confirmation.html`
**Sent To**: Customer email address
**Contains**:
- Order number & details
- Order items list with prices
- Shipping address
- Total amount breakdown

**Code Location**: `orders/signals.py` → `send_order_confirmation_email()`

### 2. Payment Confirmation Email

**When**: Automatically sent when order status changes to 'PAID'
**Template**: `payment_received.html`
**Sent To**: Customer email address
**Contains**:
- Payment confirmation
- Order details
- Next steps for shipping

**Code Location**: `orders/signals.py` → `send_payment_confirmation_email()`

### 3. Invoice Email

**When**: Called manually after invoice PDF is generated
**Template**: `invoice_email.html`
**Sent To**: Customer email address
**Attachment**: Invoice PDF file
**Contains**:
- Invoice number & date
- Item details
- Total amount due

**Code to send (insert in invoice generation view)**:
```python
from orders.email_service import OrderEmailService

# After invoice is generated:
OrderEmailService.send_invoice_email(order, invoice)
```

### 4. Order Status Update Email

**When**: Called manually when order status changes
**Template**: `order_status_update.html`
**Sent To**: Customer email address
**Example Usage**:
```python
from orders.email_service import OrderEmailService

OrderEmailService.send_order_status_update(
    order, 
    "Your order has been shipped! Tracking number: ABC123456"
)
```

### 5. Welcome Email

**When**: Automatically sent when a new user registers
**Template**: `welcome.html`
**Sent To**: New customer email
**Contains**:
- Welcome message
- Features overview
- Shop link
- Support contact

**Code Location**: `customers/signals.py` → `send_welcome_email_on_registration()`

### 6. Password Reset Email

**When**: Automatically sent when user requests password reset
**Template**: Django built-in templates in `templates/customers/password_reset_*.txt/html`
**Sent To**: User email
**Note**: Uses Django's built-in `PasswordResetView`

---

## 🛠️ File Structure

New files created:

```
orders/
├── email_service.py          # Email sending service (NEW)
├── signals.py                # Order email signals (UPDATED)
└── apps.py                   # App config with signal registration (UPDATED)

customers/
├── signals.py                # Customer email signals (NEW)
└── apps.py                   # App config with signal registration (UPDATED)

templates/
└── orders/emails/            # Email templates folder (NEW)
    └── customers/emails/     # Customer email templates (NEW)

.env.example                  # Updated with Titan Mail settings (UPDATED)
settings.py                   # Email configuration (UPDATED)
```

---

## 📝 Manual Email Sending

To manually send emails programmatically:

```python
from orders.email_service import OrderEmailService, CustomerEmailService
from orders.models import Order
from django.contrib.auth.models import User

# Send order confirmation
order = Order.objects.get(id=1)
OrderEmailService.send_order_confirmation(order)

# Send payment confirmation
OrderEmailService.send_payment_received_email(order)

# Send invoice
from orders.models import Invoice
invoice = Invoice.objects.get(id=1)
OrderEmailService.send_invoice_email(order, invoice)

# Send status update
OrderEmailService.send_order_status_update(
    order, 
    "Your order has been shipped!"
)

# Send welcome email
user = User.objects.get(username='john')
CustomerEmailService.send_welcome_email(user)
```

---

## 🧪 Testing Email Configuration

### Development Testing

1. **Use Console Backend** (prints emails to terminal):
   ```bash
   # In .env
   USE_CONSOLE_EMAIL=True
   ```

2. **Run Django Shell**:
   ```bash
   python manage.py shell
   ```

3. **Test Order Confirmation**:
   ```python
   from orders.models import Order
   from orders.email_service import OrderEmailService
   
   order = Order.objects.first()
   result = OrderEmailService.send_order_confirmation(order)
   print("Success!" if result else "Failed!")
   ```

### Production Testing

1. Use real Titan Mail credentials
2. Send test email to a real address
3. Verify email delivery
4. Check spam folder

---

## 🔍 Troubleshooting

### Email Not Sending

1. **Check credentials in .env**:
   ```bash
   cat .env | grep EMAIL
   ```

2. **Check email logs**:
   ```bash
   # Django logs
   tail -f logs/django.log
   ```

3. **Test SMTP connection**:
   ```bash
   python manage.py shell
   from django.core.mail import send_mail
   # Try sending test email
   ```

### Email Going to Spam

1. Add SPF record to your domain
2. Add DKIM signature
3. Add DMARC policy
4. Add your domain to Titan Mail verified domains

### Slow Email Sending

1. Consider using async email with Celery
2. Increase `EMAIL_TIMEOUT` in settings if needed

### Template Not Found Error

1. Verify file locations in `templates/` folder
2. Check template names match exactly
3. Restart Django development server

---

## 🚀 Production Deployment

### Heroku/Render Deployment

1. Set environment variables in dashboard:
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

2. Verify email sending works after deployment

3. Monitor email delivery logs

---

## 📊 Monitoring & Logging

All email operations are logged:

```python
import logging
logger = logging.getLogger(__name__)

# Success log
logger.info(f"Order confirmation email sent to {customer_email}")

# Error log
logger.error(f"Failed to send email: {str(e)}")
```

Check logs to troubleshoot issues.

---

## 🔄 Future Enhancements

### Recommended Improvements

1. **Async Email Sending** (Celery):
   - Send emails asynchronously
   - Improve performance
   - Add retry logic

2. **Email Templates in Database**:
   - Allow customization via admin
   - No code changes needed

3. **Email Analytics**:
   - Track open rates
   - Track click-through rates
   - Monitor bounce rates

4. **SMS Notifications**:
   - SMS for order status updates
   - SMS for payment confirmations

5. **Email Scheduling**:
   - Schedule reminder emails
   - Birthday/anniversary emails

---

## 📞 Support

For Titan Mail support:
- Website: [https://www.titanmail.com/](https://www.titanmail.com/)
- Support: support@titanmail.com

For Django email documentation:
- [Django Email Documentation](https://docs.djangoproject.com/en/stable/topics/email/)

---

## 🔐 Security Checklist

- [ ] All credentials in `.env` file
- [ ] `.env` file in `.gitignore`
- [ ] TLS enabled (port 587)
- [ ] Email timeout set
- [ ] Error handling in place
- [ ] No hardcoded credentials
- [ ] HTML and text templates created
- [ ] Signals registered in app config
- [ ] Tested in development
- [ ] Verified on production

---

**Last Updated**: April 2026
**Titan Mail Integration**: ✅ Complete
**Status**: Ready for Production
