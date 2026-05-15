import os

filepath = r'templates/base.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            {% if session.get('role') == 'admin' %}
            <a href="/admin-job-alert"
              class="text-sm font-medium text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1.5 border border-amber-500/20 bg-amber-500/10 px-3 py-1 rounded-full shadow-[0_0_10px_rgba(245,158,11,0.2)]">
              <i class="fas fa-shield-alt opacity-70"></i> ADMIN
            </a>
            {% endif %}"""

if target in content:
    content = content.replace(target, '')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Removed Admin Dashboard link')
else:
    print('Target not found')
