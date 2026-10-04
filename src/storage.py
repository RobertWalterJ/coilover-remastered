# -*- coding: utf-8 -*-
"""Fence this app's saved data off from the original Coilover's.

THE BUG. localStorage is keyed by ORIGIN, not by folder, and every one of
Robert's apps sits on `https://robertwalterj.github.io/`. This fork inherited
the original game's key names verbatim:

    coilover.v1        the career save: points, unlocks, records, fitted parts
    coilover.clock     does time pass
    coilover.map       which map you were on
    coilover.pedal     pedal layout
    coilover.veh       which truck you had

The original Coilover at `/coilover/` writes exactly the same five names. They
are not two saves that happen to look alike, they are ONE save that both games
read and write. Playing either one overwrites the other: career totals, the
vehicles you had unlocked, and now the parts fitted in the garage. Rule 7 of
PWA-IDENTITY-RULES.md exists for precisely this.

THE FIX, and why it does not cost him his progress. The keys become
`coilover-remastered.*`, and on first run the old values are copied across if
the new ones are not there yet. So this app opens with the progress he has
now, the original keeps its own copy under the old names, and from this point
the two stop treading on each other.

The copy is one way and runs once. After it, nothing in this app ever touches
a `coilover.` key again.

A note on what cannot be recovered: because the two have shared one save until
today, whatever is there now is the state whichever game he played last left
behind. There is no way to separate them retrospectively. This stops it
getting worse, starting from where he actually is.
"""
import io

p = 'game.html'
s = io.open(p, encoding='utf-8').read()
n = 0

def sub(old, new, count=1):
    global s, n
    assert old in s, 'MISS: ' + old[:110].replace('\n', ' | ')
    assert s.count(old) == count, 'EXPECTED %d, FOUND %d: %s' % (count, s.count(old), old[:70])
    s = s.replace(old, new); n += count

# ---------------------------------------------------------------- the keys
sub("var SAVEKEY='coilover.v1';",
    r"""/* ---- this app's own corner of localStorage ----
   One origin serves every app Robert publishes, so a key name is a shared
   name. These used to be the original Coilover's keys exactly, which meant
   the two games shared one save and overwrote each other. See src/storage.py. */
var SAVEKEY='coilover-remastered.v1';
var LS_CLOCK='coilover-remastered.clock', LS_MAP='coilover-remastered.map',
    LS_PEDAL='coilover-remastered.pedal', LS_VEH='coilover-remastered.veh';

/* Carry his progress over once, rather than starting him at zero. Runs before
   anything reads a key, copies only what is not already here, and never
   writes back to the old names. */
(function(){
  try{
    var moves=[[SAVEKEY,'coilover.v1'], [LS_CLOCK,'coilover.clock'],
               [LS_MAP,'coilover.map'], [LS_PEDAL,'coilover.pedal'],
               [LS_VEH,'coilover.veh']];
    for(var i=0;i<moves.length;i++){
      var to=moves[i][0], from=moves[i][1];
      if(localStorage.getItem(to)===null){
        var v=localStorage.getItem(from);
        if(v!==null) localStorage.setItem(to,v);
      }
    }
  }catch(_){}
})();""")

# ------------------------------------------------------------- the writers
sub("localStorage.setItem('coilover.clock',String(m))",
    "localStorage.setItem(LS_CLOCK,String(m))")
sub("localStorage.setItem('coilover.map',String(i))",
    "localStorage.setItem(LS_MAP,String(i))")
sub("localStorage.setItem('coilover.pedal',String(m))",
    "localStorage.setItem(LS_PEDAL,String(m))")
sub("localStorage.setItem('coilover.veh',String(i))",
    "localStorage.setItem(LS_VEH,String(i))")

# ------------------------------------------------------------- the readers
sub("localStorage.getItem('coilover.pedal')", "localStorage.getItem(LS_PEDAL)")
sub("localStorage.getItem('coilover.clock')", "localStorage.getItem(LS_CLOCK)")
sub("localStorage.getItem('coilover.map')",   "localStorage.getItem(LS_MAP)")
sub("localStorage.getItem('coilover.veh')",   "localStorage.getItem(LS_VEH)")

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('applied:', n)

# Nothing may be left pointing at the shared names except the one way copy.
left = [l for l in s.split('\n') if "'coilover." in l and 'moves=' not in l
        and "coilover.v1'" not in l and "coilover.clock'" not in l
        and "coilover.map'" not in l and "coilover.pedal'" not in l
        and "coilover.veh'" not in l]
print('stray shared keys:', len(left))
