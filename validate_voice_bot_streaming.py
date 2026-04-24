#!/usr/bin/env python
"""
Voice Bot Streaming - System Validation Script

Validates that all components are properly installed and configured
"""

import sys
import os

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    if package_name is None:
        package_name = module_name
    
    try:
        __import__(module_name)
        print(f"✓ {package_name} installed")
        return True
    except ImportError as e:
        print(f"✗ {package_name} NOT installed - {str(e)}")
        return False

def check_django_config():
    """Check Django configuration"""
    print("\n=== Django Configuration ===")
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'shopping_store.settings')
        django.setup()
        
        from django.conf import settings
        
        # Check ASGI
        asgi_app = getattr(settings, 'ASGI_APPLICATION', None)
        if asgi_app:
            print(f"✓ ASGI_APPLICATION configured: {asgi_app}")
        else:
            print("✗ ASGI_APPLICATION not configured")
        
        # Check Channels
        if 'channels' in settings.INSTALLED_APPS:
            print("✓ Channels in INSTALLED_APPS")
        else:
            print("✗ Channels NOT in INSTALLED_APPS")
        
        # Check voice_bot
        if 'voice_bot' in settings.INSTALLED_APPS:
            print("✓ voice_bot in INSTALLED_APPS")
        else:
            print("✗ voice_bot NOT in INSTALLED_APPS")
        
        # Check channel layers
        channel_layers = getattr(settings, 'CHANNEL_LAYERS', None)
        if channel_layers:
            print(f"✓ CHANNEL_LAYERS configured")
            backend = channel_layers.get('default', {}).get('BACKEND', '')
            print(f"  Backend: {backend.split('.')[-1]}")
        else:
            print("✗ CHANNEL_LAYERS not configured")
        
        return True
    except Exception as e:
        print(f"✗ Django configuration error: {str(e)}")
        return False

def check_models():
    """Check if models exist"""
    print("\n=== Models ===")
    try:
        from voice_bot.models import VoiceQuery, VoiceQueryLog
        
        query_fields = [f.name for f in VoiceQuery._meta.get_fields()]
        print(f"✓ VoiceQuery model exists with {len(query_fields)} fields")
        
        log_fields = [f.name for f in VoiceQueryLog._meta.get_fields()]
        print(f"✓ VoiceQueryLog model exists with {len(log_fields)} fields")
        
        return True
    except Exception as e:
        print(f"✗ Models error: {str(e)}")
        return False

def check_voice_bot_modules():
    """Check if voice_bot modules exist"""
    print("\n=== Voice Bot Modules ===")
    
    modules = [
        'voice_bot.stt',
        'voice_bot.intent',
        'voice_bot.services',
        'voice_bot.tts',
        'voice_bot.views',
        'voice_bot.consumers',
        'voice_bot.routing',
        'voice_bot.streaming',
    ]
    
    all_ok = True
    for module in modules:
        if check_import(module, module.split('.')[-1]):
            pass
        else:
            all_ok = False
    
    return all_ok

def check_files():
    """Check if all required files exist"""
    print("\n=== Files ===")
    
    files = [
        'voice_bot/models.py',
        'voice_bot/stt.py',
        'voice_bot/intent.py',
        'voice_bot/services.py',
        'voice_bot/tts.py',
        'voice_bot/views.py',
        'voice_bot/urls.py',
        'voice_bot/consumers.py',
        'voice_bot/routing.py',
        'voice_bot/streaming.py',
        'shopping_store/asgi.py',
        'templates/voice_bot_streaming.html',
    ]
    
    all_ok = True
    for file_path in files:
        full_path = os.path.join('shopping_store', file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✓ {file_path} ({size} bytes)")
        else:
            print(f"✗ {file_path} NOT FOUND")
            all_ok = False
    
    return all_ok

def check_dependencies():
    """Check all Python dependencies"""
    print("\n=== Python Dependencies ===")
    
    packages = [
        ('channels', 'Channels'),
        ('whisper', 'OpenAI Whisper'),
        ('gtts', 'Google Text-to-Speech'),
        ('librosa', 'Librosa'),
        ('soundfile', 'SoundFile'),
        ('websockets', 'WebSockets'),
    ]
    
    all_ok = True
    for module, name in packages:
        if check_import(module, name):
            pass
        else:
            all_ok = False
    
    return all_ok

def main():
    print("=" * 60)
    print("Voice Bot Streaming - System Validation")
    print("=" * 60)
    
    results = []
    
    # Run checks
    results.append(("Dependencies", check_dependencies()))
    results.append(("Files", check_files()))
    results.append(("Django Config", check_django_config()))
    results.append(("Models", check_models()))
    results.append(("Modules", check_voice_bot_modules()))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n✅ All checks passed! System is ready.")
        print("\nNext steps:")
        print("1. python manage.py runserver")
        print("2. Open http://localhost:8000/voice-bot-streaming/")
        print("3. Click 'Start Recording' and speak a query")
        print("4. Watch real-time transcription and intent detection")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please review the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
