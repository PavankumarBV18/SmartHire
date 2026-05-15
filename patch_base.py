import os

filepath = r'templates/base.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """          <a href="/admin-job-alert"
            class="text-sm font-medium text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1.5 border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 rounded-full">
            <i class="fas fa-shield-alt opacity-70"></i> Admin Panel
          </a>"""

replacement = """          {% if session.get('user') %}
            {% if session.get('role') == 'admin' %}
            <a href="/admin-job-alert"
              class="text-sm font-medium text-amber-400 hover:text-amber-300 transition-colors flex items-center gap-1.5 border border-amber-500/20 bg-amber-500/10 px-3 py-1 rounded-full shadow-[0_0_10px_rgba(245,158,11,0.2)]">
              <i class="fas fa-shield-alt opacity-70"></i> ADMIN
            </a>
            {% endif %}
            
            <a href="/subscription" class="text-sm font-medium transition-colors flex items-center gap-1.5 px-3 py-1 rounded-full 
              {% if session.get('role') == 'admin' %} text-indigo-400 bg-indigo-500/10 border border-indigo-500/20
              {% elif session.get('plan') == 'premium' %} text-amber-400 bg-amber-500/10 border border-amber-500/20
              {% else %} text-slate-300 bg-slate-800 border border-slate-700 {% endif %}">
              <i class="fas fa-crown"></i> 
              {% if session.get('role') == 'admin' %} ADMIN
              {% elif session.get('plan') == 'premium' %} PREMIUM USER
              {% else %} FREE USER {% endif %}
            </a>
            
            <div class="relative group">
              <button class="flex items-center gap-2 text-sm font-medium text-slate-300 hover:text-white transition-colors py-2">
                <i class="fas fa-user-circle text-lg opacity-80"></i>
                <span class="max-w-[100px] truncate">{{ session.get('user').split('@')[0] }}</span>
                <i class="fas fa-chevron-down text-xs opacity-50"></i>
              </button>
              <div class="absolute right-0 top-full mt-2 w-48 bg-slate-800 border border-slate-700 rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 transform origin-top-right group-hover:scale-100 scale-95 z-50">
                <div class="p-2">
                  <a href="/saved-resumes?email={{ session.get('user') }}" class="block px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white rounded-lg transition-colors">
                    <i class="fas fa-file-alt mr-2 opacity-70"></i> My Resumes
                  </a>
                  <div class="h-px bg-slate-700/50 my-1"></div>
                  <a href="/logout" class="block px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors">
                    <i class="fas fa-sign-out-alt mr-2 opacity-70"></i> Logout
                  </a>
                </div>
              </div>
            </div>
          {% else %}
            <a href="/login" class="text-sm font-medium text-slate-300 hover:text-white transition-colors flex items-center gap-1.5 py-2">
              <i class="fas fa-sign-in-alt opacity-50"></i> Login
            </a>
            <a href="/register" class="text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-colors px-4 py-1.5 rounded-full shadow-lg shadow-indigo-500/25">
              Sign Up
            </a>
          {% endif %}"""

if target in content:
    content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Navbar replaced successfully')
else:
    print('Target not found in base.html')
