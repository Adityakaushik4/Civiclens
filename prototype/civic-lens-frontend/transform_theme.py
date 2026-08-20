import os
import glob
import re

files = glob.glob('src/**/*.tsx', recursive=True)

replacements = {
    # Backgrounds
    r'bg-slate-950': 'bg-white',
    r'bg-slate-900/80': 'bg-white/90',
    r'bg-slate-900/60': 'bg-white/80',
    r'bg-slate-900/40': 'bg-white/60',
    r'bg-slate-900': 'bg-white',
    
    r'bg-slate-800/80': 'bg-slate-50/80',
    r'bg-slate-800/60': 'bg-slate-50/60',
    r'bg-slate-800/40': 'bg-slate-50/40',
    r'bg-slate-800': 'bg-slate-50',
    
    # Borders
    r'border-slate-800': 'border-slate-200',
    r'border-slate-700': 'border-slate-300',
    
    # Text colors
    r'text-white': 'text-slate-900',
    r'text-slate-200': 'text-slate-800',
    r'text-slate-300': 'text-slate-700',
    r'text-slate-400': 'text-slate-600',
    
    # Border radius
    r'rounded-3xl': 'rounded-xl',
    r'rounded-2xl': 'rounded-lg',
    
    # Shadows
    r'shadow-emerald-500/20': 'shadow-sm',
    r'shadow-blue-500/20': 'shadow-sm',
    r'shadow-blue-500/10': 'shadow-sm',
    r'shadow-indigo-500/20': 'shadow-sm',
    
    # Gradients to solid
    r'bg-gradient-to-r from-blue-600 to-indigo-600': 'bg-blue-700',
    r'bg-gradient-to-r from-emerald-600 to-teal-600': 'bg-teal-600',
    r'bg-gradient-to-r from-slate-900 to-slate-800': 'bg-white',
    r'hover:from-emerald-500 hover:to-teal-500': 'hover:bg-teal-700',
    r'hover:from-blue-500 hover:to-indigo-500': 'hover:bg-blue-800',
    
    # Action buttons
    r'bg-blue-600/20': 'bg-blue-100',
    r'text-blue-300': 'text-blue-700',
    r'border-blue-500/30': 'border-blue-200',
    r'bg-indigo-600/20': 'bg-indigo-100',
    r'text-indigo-300': 'text-indigo-700',
    r'border-indigo-500/30': 'border-indigo-200',
    
    # Auth page fixes
    r'from-slate-950': 'from-slate-100',
    r'to-slate-900': 'to-white',
}

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = content
    for pattern, repl in replacements.items():
        # Use simple string replace since Tailwind classes are space/quote bounded in JSX
        # We can just use string replace to be completely safe against Regex weirdness, 
        # but we need to ensure we don't partially replace, e.g. "bg-slate-900" inside "bg-slate-900/80".
        # Since Python dicts are ordered by insertion, we listed the /80, /60 ones first, so simple replace is safe!
        new_content = new_content.replace(pattern, repl)
        
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
