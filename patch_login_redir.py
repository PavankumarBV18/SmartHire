import os

filepath = r'app.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                        if u.get('role') == 'admin':
                            return redirect('/admin-job-alert')"""
if target in content:
    content = content.replace(target, '')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Removed admin redirect')
else:
    print('Target not found')
