import os
import re

filepath = r'templates/subscription.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("session.get('role') == 'admin'", "session.get('user') == 'smarthire72@gmail.com' or session.get('role') == 'admin'")
content = content.replace("session.get('role') != 'admin'", "session.get('user') != 'smarthire72@gmail.com' and session.get('role') != 'admin'")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated subscription.html')
