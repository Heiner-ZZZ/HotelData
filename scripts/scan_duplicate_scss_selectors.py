#!/usr/bin/env python3
"""
Scans all partials directories under frontend/src for duplicate CSS selectors
between layout files and their corresponding content/actions files.
"""
import os, re

BASE = 'frontend/src'

def extract_top_level_selectors(filepath):
    """Extract top-level CSS selectors from a SCSS file."""
    selectors = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except:
        return selectors

    # Remove comments
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    # Find top-level selectors (not nested, not inside @media/@keyframes/etc)
    # Look for patterns like: .selector { or #selector { or selector {
    # at the start of a line or after a closing brace
    lines = content.split('\n')
    brace_depth = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip @-rules and mixins
        if stripped.startswith('@') or stripped.startswith('&'):
            continue
        # Check if this is a selector at depth 0
        if brace_depth == 0:
            m = re.match(r'^([.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*(?:\s*,\s*[.#]?[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*)*)\s*\{', stripped)
            if m:
                sel = m.group(1).strip()
                selectors.add(sel)

        # Track brace depth
        brace_depth += stripped.count('{') - stripped.count('}')

    return selectors

def main():
    results = []

    for root, dirs, files in os.walk(BASE):
        if 'partials' not in root:
            continue

        layout_file = None
        content_file = None
        actions_file = None

        for f in sorted(files):
            if not f.endswith('.scss'):
                continue
            fname = f.replace('.scss', '')
            if 'layout' in fname.lower():
                layout_file = os.path.join(root, f)
            elif 'content' in fname.lower():
                content_file = os.path.join(root, f)
            elif 'actions' in fname.lower():
                actions_file = os.path.join(root, f)

        if not layout_file:
            continue

        layout_selectors = extract_top_level_selectors(layout_file)

        for label, target_file in [('content', content_file), ('actions', actions_file)]:
            if not target_file:
                continue
            target_selectors = extract_top_level_selectors(target_file)
            duplicates = layout_selectors & target_selectors
            if duplicates:
                feature = root.replace(BASE + '/app/features/', '').replace('/pages/', '/').replace('/components/', '/').replace('/partials', '')
                results.append({
                    'feature': feature,
                    'layout_file': layout_file,
                    'target_file': target_file,
                    'target_type': label,
                    'duplicates': sorted(duplicates)
                })

    # Print results
    if not results:
        print("✅ NO duplicate selectors found between any layout↔content/actions pairs!")
    else:
        print(f"🔍 Found {len(results)} files with duplicate selectors:\n")
        for r in sorted(results, key=lambda x: x['feature']):
            print(f"📁 {r['feature']}")
            print(f"   {r['target_type']}: {os.path.basename(r['target_file'])}")
            print(f"   Duplicates ({len(r['duplicates'])}): {', '.join(r['duplicates'])}")
            print()

if __name__ == '__main__':
    main()
