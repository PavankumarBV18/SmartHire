import os

filepath = r'templates/login.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('Authenticate', 'Welcome Back')
content = content.replace('Access the Command Center', 'Sign in to your account')
content = content.replace('admin@gmail.com', 'john@example.com')
content = content.replace('Restricted Area?', 'New here?')
content = content.replace('Request Clearances', 'Sign Up')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print('Updated login.html')
