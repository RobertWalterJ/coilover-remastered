# -*- coding: utf-8 -*-
"""Build the two published copies from src/game.html, which is the source.

  src/game.html  the source: a fragment, three.js and the loader off a CDN
  docs/          the built game: full document, three.js and GLTFLoader
                 vendored, PWA head, service worker. This one folder is what
                 GitHub Pages publishes AND what server.mjs serves locally.

There is deliberately only ONE build output. An earlier version wrote app/ and
then copied it to docs/, which meant every 13 MB road mesh was committed
twice and the two could drift. Edit src/game.html and run this.
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
io.open('docs/index.html', 'w', encoding='utf-8', newline='\n').write(doc)
print('docs/index.html written:', os.path.getsize('docs/index.html'), 'bytes')

# Pages must not run Jekyll over it (underscore-prefixed paths vanish if it does)
io.open('docs/.nojekyll', 'w').write('')
