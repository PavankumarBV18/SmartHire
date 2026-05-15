import os
import re

filepath = r'app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            user = get_current_user()
            is_premium = user and (user.get('role') == 'admin' or user.get('plan') == 'premium')
            if not is_premium and num_questions > 2:"""

replacement = """            user = get_current_user()
            is_premium = session.get('user') == 'smarthire72@gmail.com' or (user and (user.get('role') == 'admin' or user.get('plan') == 'premium'))
            if not is_premium and num_questions > 2:"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated interview premium check')
else:
    print('Target not found in app.py')
