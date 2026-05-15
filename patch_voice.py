import re

filepath = 'templates/base.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    function toggleVoiceInput(e) {
      if (e) e.preventDefault();"""
      
replacement = """    function toggleVoiceInput(e) {
      if (e) e.preventDefault();
      
      const isPremium = "{{ 'true' if session.get('user') == 'smarthire72@gmail.com' or session.get('role') == 'admin' or session.get('plan') == 'premium' else 'false' }}" === "true";
      if (!isPremium) {
          window.location.href = "/premium-locked";
          return;
      }"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Patched voice assistant access')
else:
    print('Target not found')
