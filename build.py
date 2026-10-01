# -*- coding: utf-8 -*-
"""Build the two published copies from src/game.html, which is the source.

  src/game.html  the Artifact copy: a fragment, three.js off a CDN
  app/           the installable copy: full document, three.js vendored, PWA
  docs/          the same thing again, because that is what GitHub Pages serves

app/ and docs/ are byte for byte identical and both are generated. Edit
src/game.html and run this; never edit either output by hand.
"""
import io, os, shutil

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

frag = io.open('src/game.html', encoding='utf-8').read()
frag = frag.replace(
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>',
    '<script src="vendor/three.min.js"></script>')
# The model loader, vendored for the same reason: the installed copy must run
# with no network at all.
frag = frag.replace(
    '<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>',
    '<script src="vendor/GLTFLoader.js"></script>')

head_extra = '''<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="theme-color" content="#17121b">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<style>html,body{margin:0;height:100%;background:#1a1016}img{max-width:100%}[hidden]{display:none!important}</style>
'''

cut = frag.index('<div id="stage">')
head, body = frag[:cut], frag[cut:]

doc = ('<!doctype html>\n<html lang="en">\n<head>\n' + head_extra + head +
       '</head>\n<body>\n' + body + '''<script>
if('serviceWorker' in navigator) addEventListener('load',function(){
  navigator.serviceWorker.register('sw.js').catch(function(){});
});
</script>
</body>
</html>
''')
io.open('app/index.html', 'w', encoding='utf-8', newline='\n').write(doc)
print('app/index.html written:', os.path.getsize('app/index.html'), 'bytes')

# ---- and the copy GitHub Pages serves ---------------------------------------
# Generated rather than committed twice by hand, so docs/ cannot drift from
# app/ the way a copied folder always eventually does.
if os.path.isdir('docs'):
    shutil.rmtree('docs')
shutil.copytree('app', 'docs')
io.open('docs/.nojekyll', 'w').write('')     # Pages must not run Jekyll over it
print('docs/ written from app/')
