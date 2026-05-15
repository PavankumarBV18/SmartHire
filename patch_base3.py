import os
import re

filepath = r'templates/base.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """            <a href="/subscription" class="text-sm font-medium transition-colors flex items-center gap-1.5 px-3 py-1 rounded-full 
              {% if session.get('role') == 'admin' %} text-indigo-400 bg-indigo-500/10 border border-indigo-500/20
              {% elif session.get('plan') == 'premium' %} text-amber-400 bg-amber-500/10 border border-amber-500/20
              {% else %} text-slate-300 bg-slate-800 border border-slate-700 {% endif %}">
              <i class="fas fa-crown"></i> 
              {% if session.get('role') == 'admin' %} ADMIN
              {% elif session.get('plan') == 'premium' %} PREMIUM USER
              {% else %} FREE USER {% endif %}
            </a>"""

replacement = """            <a href="/subscription" class="text-sm font-medium transition-colors flex items-center gap-1.5 px-3 py-1 rounded-full 
              {% if session.get('user') == 'smarthire72@gmail.com' or session.get('role') == 'admin' %} text-indigo-400 bg-indigo-500/10 border border-indigo-500/20
              {% elif session.get('plan') == 'premium' %} text-amber-400 bg-amber-500/10 border border-amber-500/20
              {% else %} text-slate-300 bg-slate-800 border border-slate-700 {% endif %}">
              <i class="fas fa-crown"></i> 
              {% if session.get('user') == 'smarthire72@gmail.com' or session.get('role') == 'admin' %} ADMIN
              {% elif session.get('plan') == 'premium' %} PREMIUM USER
              {% else %} FREE USER {% endif %}
            </a>"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated base.html badges')
else:
    print('Target not found in base.html')
