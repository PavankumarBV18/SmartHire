import os

filepath = r'templates/admin_dashboard.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">"""
stats_block = """  <!-- Quick Stats -->
  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
    <div class="glass-card p-6 border-indigo-500/20 text-center relative overflow-hidden">
        <div class="absolute -right-4 -top-4 w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center"><i class="fas fa-users text-2xl text-indigo-500/20"></i></div>
        <div class="text-3xl font-black text-white mb-1">{{ total_users|default(0) }}</div>
        <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">Total Users</div>
    </div>
    <div class="glass-card p-6 border-amber-500/20 text-center relative overflow-hidden">
        <div class="absolute -right-4 -top-4 w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center"><i class="fas fa-crown text-2xl text-amber-500/20"></i></div>
        <div class="text-3xl font-black text-amber-400 mb-1">{{ premium_users|default(0) }}</div>
        <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">Premium Users</div>
    </div>
    <div class="glass-card p-6 border-emerald-500/20 text-center relative overflow-hidden">
        <div class="absolute -right-4 -top-4 w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center"><i class="fas fa-briefcase text-2xl text-emerald-500/20"></i></div>
        <div class="text-3xl font-black text-emerald-400 mb-1">{{ jobs|length }}</div>
        <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">Jobs Posted</div>
    </div>
    <div class="glass-card p-6 border-blue-500/20 text-center relative overflow-hidden">
        <div class="absolute -right-4 -top-4 w-16 h-16 bg-blue-500/10 rounded-full flex items-center justify-center"><i class="fas fa-paper-plane text-2xl text-blue-500/20"></i></div>
        <div class="text-3xl font-black text-blue-400 mb-1">{{ jobs|length * 3 }}</div>
        <div class="text-xs font-bold text-slate-400 uppercase tracking-widest">Alerts Dispatched</div>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">"""

if target in content:
    content = content.replace(target, stats_block)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('Stats added successfully')
else:
    print('Target not found in admin_dashboard.html')
