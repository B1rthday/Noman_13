import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
SR=44100; DUR=48.0; N=int(SR*DUR)
rng=np.random.default_rng(13)
BPM=120; BEAT=60/BPM; BAR=4*BEAT
def hz(m): return 440.0*2**((m-69)/12)
def lp(x,f,o=2): return sosfilt(butter(o,min(f,20000)/(SR/2),'low',output='sos'),x)
def hp(x,f,o=2): return sosfilt(butter(o,f/(SR/2),'high',output='sos'),x)
def bp(x,a,b,o=2): return sosfilt(butter(o,[a/(SR/2),b/(SR/2)],'band',output='sos'),x)
def tt(d): return np.arange(int(d*SR))/SR
def saw(f,t): return 2*((f*t)%1.0)-1
class Bus:
    def __init__(s): s.L=np.zeros(N,np.float32); s.R=np.zeros(N,np.float32)
    def add(s,t0,x,g=1.0,pan=0.0):
        i=int(t0*SR)
        if i>=N or i+len(x)<=0: return
        a=max(0,-i); x=x[a:]; i=max(i,0); n=min(len(x),N-i); x=x[:n]
        l=np.cos((pan+1)*np.pi/4); r=np.sin((pan+1)*np.pi/4)
        s.L[i:i+n]+=x*g*l*1.414; s.R[i:i+n]+=x*g*r*1.414
def fade(x,a=0.005,b=0.01):
    x=x.copy(); na=int(a*SR); nb=int(b*SR)
    if na: x[:na]*=np.linspace(0,1,na)
    if nb: x[-nb:]*=np.linspace(1,0,nb)
    return x
# --- chords (D A Bm G)
PROG=[(50,[62,66,69]),(45,[61,64,69]),(47,[62,66,71]),(43,[62,67,71])]
HOOK=[[78,81,83,81],[76,81,85,81],[78,83,86,83],[79,83,86,83]]
ARP=[[62,66,69,74],[61,64,69,73],[62,66,71,74],[62,67,71,74]]
def chord(b): return PROG[b%4]
# --- instruments
def pad_note(m,d):
    t=tt(d); x=0
    for c in (-8,0,8): x=x+saw(hz(m)*2**(c/1200),t)
    return x/3
def pluck(m,d=0.5,bright=1.0):
    t=tt(d); f=hz(m)
    x=np.sin(2*np.pi*f*t)*np.exp(-t*5)+0.45*np.sin(2*np.pi*2*f*t)*np.exp(-t*9)+0.2*np.sin(2*np.pi*3*f*t+1)*np.exp(-t*14)*bright
    return fade(x,0.002,0.02)
def piano(m,d=1.6):
    t=tt(d); f=hz(m); x=0
    for k,(a,dc) in enumerate([(1,2.2),(0.5,3.2),(0.25,4.5),(0.12,6),(0.06,8)],1):
        x=x+a*np.sin(2*np.pi*f*k*t*(1+0.0003*k*k))*np.exp(-t*dc)
    x=x*(1-np.exp(-t*300))
    return fade(x,0.001,0.05)
def lead(m,d=0.6):
    t=tt(d); x=0
    for c in (-9,0,9): x=x+saw(hz(m)*2**(c/1200),t)
    x=lp(x/3,4200)*np.exp(-t*4.5)*(1-np.exp(-t*200))
    return fade(x,0.002,0.03)
def kick(g=1):
    t=tt(0.45); f=45+110*np.exp(-t*28); ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)*np.exp(-t*9); x+=0.25*np.sin(2*np.pi*2400*t)*np.exp(-t*160)
    return np.tanh(x*1.4)*g
def clap(g=1):
    t=tt(0.28); n=rng.standard_normal(len(t)); n=bp(n,1100,3800)
    env=np.exp(-t*22)+0.6*np.exp(-((t-0.012)%0.02)*0)*0
    for k in (0.0,0.011,0.022): env+=np.where(t>=k,np.exp(-(t-k)*90),0)*0.5
    return n*env*g*1.2
def hat(g=1,op=False):
    d=0.22 if op else 0.07; t=tt(d); n=hp(rng.standard_normal(len(t)),7000)
    return n*np.exp(-t*(18 if op else 70))*g
def bass(m,d=0.24):
    t=tt(d); f=hz(m); x=np.sin(2*np.pi*f*t)+0.35*lp(saw(f,t),700)
    return fade(x*np.exp(-t*3.5),0.004,0.03)
def noise_rise(d,f0=800):
    t=tt(d); n=hp(rng.standard_normal(len(t)),f0)
    env=(t/d)**2.2
    sw=np.sin(2*np.pi*np.cumsum(300*(2**(3.2*t/d)))/SR)*0.25
    return (n*0.8+sw)*env
def boom(d=1.8):
    t=tt(d); f=34+60*np.exp(-t*14); ph=2*np.pi*np.cumsum(f)/SR
    x=np.sin(ph)*np.exp(-t*2.4)
    n=lp(rng.standard_normal(len(t)),2500)*np.exp(-t*9)*0.6
    return x+n
def whoosh(d=0.8):
    t=tt(d); n=rng.standard_normal(len(t)); x=bp(n,500,5000)*np.sin(np.pi*t/d)**2
    return x
def snare_roll(t0,t1,bus,g=1.0,start_div=0.25):
    t=t0; 
    while t<t1-0.01:
        p=(t-t0)/(t1-t0); step=BEAT*start_div*(1-0.6*p)
        bus.add(t,clap(0.35+0.65*p)*g,1,0.0); t+=step
def reverb(L,R,sec=2.2,decay=3.0):
    t=tt(sec); out=[]
    for ch in (L,R):
        ir=rng.standard_normal(len(t))*np.exp(-t*decay); ir=lp(ir,6000)
        ir[:int(0.012*SR)]*=np.linspace(0,1,int(0.012*SR))
        out.append(fftconvolve(ch,ir)[:N].astype(np.float32)/ (np.sqrt((ir**2).sum())+1e-9))
    return out
def delay(bus,time,fb=0.35,n=3):
    L,R=bus.L.copy(),bus.R.copy(); out_l=L.copy(); out_r=R.copy()
    for k in range(1,n+1):
        s=int(time*SR*k); g=fb**k
        out_l[s:]+=R[:N-s]*g; out_r[s:]+=L[:N-s]*g
    bus.L,bus.R=out_l,out_r
def build(include_scratch=True):
    pad,arp,ld,bs,dr,fx,pn=[Bus() for _ in range(7)]
    wet=Bus()
    # ---------- timeline
    DROP1=(12,18); DROP2=(40,46)
    GATE=(6.0,7.0)
    # PADS per bar
    padgain={}
    for b in range(24):
        t0=b*BAR
        if t0<4: g,f=0.30,420+300*(t0/4)
        elif t0<10: g,f=0.30,900
        elif t0<12: g,f=0.45,900+2400*((t0-10)/2)
        elif t0<18: g,f=0.55,2600
        elif t0<28: g,f=0.36,1400
        elif t0<38: g,f=0.55,1900
        elif t0<40: g,f=0.55,1700+1800*((t0-38)/2)
        elif t0<46: g,f=0.60,2800
        else: g,f=0,0
        if g==0: continue
        r,notes=chord(b)
        x=sum(pad_note(m,BAR+0.35) for m in notes)/3+0.6*pad_note(r-12+12,BAR+0.35)*0.5
        x=lp(x,f)*np.concatenate([np.linspace(0,1,int(0.25*SR)),np.ones(int((BAR+0.35)*SR)-int(0.25*SR))])
        x=x*np.concatenate([np.ones(int(BAR*SR)),np.linspace(1,0,len(x)-int(BAR*SR))])
        pad.add(t0,x,g,0.0); wet.add(t0,x,g*0.5)
    # S1 drone
    t=tt(4.2); dr1=(np.sin(2*np.pi*hz(38)*t)+0.5*np.sin(2*np.pi*hz(45)*t))*(t/4.2)**1.5*np.exp(-np.maximum(t-4.0,0)*30)
    pad.add(0,dr1,0.35,0)
    # Final chord D (46..48) big
    for m in [50,62,66,69,74,78]:
        x=pad_note(m,2.6); x=lp(x,3600)*np.exp(-tt(2.6)*0.9)
        pad.add(46.0,fade(x,0.01,0.3),0.40,0); wet.add(46.0,fade(x,0.01,0.3),0.4)
    for k,m in enumerate([86,90,93,98]):
        pl=pluck(m,1.2); fx.add(46.05+k*0.07,pl,0.28,-0.5+k*0.33); wet.add(46.05+k*0.07,pl,0.3)
    # BASS
    def bass_bar(b,t0,vel=1.0):
        r=chord(b)[0]
        for k in range(8):
            m=r if k%2==0 else r+12
            bs.add(t0+k*BEAT/2,bass(m),0.50*vel if k%2==0 else 0.30*vel,0)
    for b in range(6,9): bass_bar(b,b*BAR)
    for b in range(20,23): bass_bar(b,b*BAR)
    # playful bass in S2 (4..6 and 7..10): root dun-dun
    for b in range(2,5):
        r=chord(b)[0]
        for k,(off,m) in enumerate([(0,r),(0.75,r),(1.0,r+7),(1.5,r+12),(1.75,r+7)]):
            tb=b*BAR+off*BEAT
            if not (GATE[0]<=tb<GATE[1]): bs.add(tb,bass(m,0.3),0.35,0)
    bs.add(7.0,bass(50,0.5),0.9,0)  # comedic return
    # bass pad for S5 (gentle)
    for b in range(15,19):
        bs.add(b*BAR,fade(bass(chord(b)[0],1.5)*1.0,0.01,0.2),0.35,0)
    # DRUMS
    def four_floor(t0,t1,g=1.0,hats=True,clap_g=0.6):
        t=t0
        while t<t1-1e-6:
            dr.add(t,kick(1.0),0.85*g,0); t+=BEAT
        t=t0+BEAT
        while t<t1-1e-6:
            dr.add(t,clap(1.0),clap_g*g,0.1); t+=2*BEAT
        t=t0+BEAT/2
        while t<t1-1e-6:
            dr.add(t,hat(1.0,True),0.22*g,0.25); t+=BEAT
        t=t0
        while t<t1-1e-6:
            dr.add(t+BEAT/4,hat(0.7),0.10*g,-0.25); dr.add(t+3*BEAT/4,hat(0.7),0.10*g,-0.25); t+=BEAT
    four_floor(*DROP1); four_floor(*DROP2)
    four_floor(30,36,g=0.55,hats=True,clap_g=0.3)
    # heartbeat S1
    for tb in (2.0,3.0,3.5): dr.add(tb,kick(0.9),0.5,0)
    # S2 light beat
    for tb in np.arange(4,10,BEAT):
        if GATE[0]<=tb<GATE[1]: continue
        if abs((tb-4)%1.0)<1e-6: dr.add(tb,kick(0.8),0.55,0)
        else: dr.add(tb,hat(0.8),0.14,0.2)
        if abs((tb-4)%2.0-1.0)<1e-6: dr.add(tb,clap(0.8),0.25,0.1)
    # S4 gentle kick on bar downbeats
    for tb in np.arange(18,26,BAR): dr.add(tb,kick(0.6),0.30,0)
    # half time 38..40
    for tb in (38.0,39.0): dr.add(tb,kick(1),0.6,0)
    for tb in (38.5,39.5): dr.add(tb,clap(1),0.4,0)
    # rolls
    snare_roll(10.0,12.0,dr,0.55,0.5); snare_roll(8.0,10.0,dr,0.25,0.5)
    snare_roll(26.0,28.0,dr,0.3,0.5); snare_roll(36.0,38.0,dr,0.5,0.5); snare_roll(39.0,40.0,dr,0.6,0.25)
    # ARP
    for b in range(2,5):
        for k in range(8):
            tb=b*BAR+k*BEAT/2
            if GATE[0]<=tb<GATE[1] or b==4 and k>=5 and False: continue
            m=ARP[b%4][k%4]+(12 if k%4==3 else 12)
            arp.add(tb,pluck(m,0.4),0.22,(-0.5 if k%2 else 0.5)); wet.add(tb,pluck(m,0.4),0.12)
    for (a,bq) in (DROP1,DROP2):
        for b in range(int(a/BAR),int(bq/BAR)):
            for k in range(8):
                m=ARP[b%4][k%4]+12
                tb=b*BAR+k*BEAT/2; arp.add(tb,pluck(m,0.4),0.20,(-0.4 if k%2 else 0.4))
    for b in range(15,19):
        for k in range(8):
            m=ARP[b%4][k%4]+12; tb=b*BAR+k*BEAT/2
            arp.add(tb,pluck(m,0.45),0.10,(-0.4 if k%2 else 0.4)); wet.add(tb,pluck(m,0.4),0.08)
    # HOOK lead in drops (quarter notes) + delay
    for (a,bq) in (DROP1,DROP2):
        for b in range(int(a/BAR),int(bq/BAR)):
            for k,m in enumerate(HOOK[b%4]):
                ld.add(b*BAR+k*BEAT,lead(m,0.55),0.42,0.0)
    # DROP2 extra octave sparkle
    for b in range(20,23):
        for k,m in enumerate(HOOK[b%4]): ld.add(b*BAR+k*BEAT+BEAT/2,lead(m+12,0.4),0.14,0.3)
    # S4 emotional piano arpeggio (slow)
    for b in range(9,14):
        notes=[chord(b)[1][0]-12,chord(b)[1][1]-12,chord(b)[1][2]-12,chord(b)[1][0],chord(b)[1][1],chord(b)[1][2],chord(b)[1][1],chord(b)[1][0]]
        for k,m in enumerate(notes):
            pn.add(b*BAR+k*BEAT/2,piano(m+12 if k>2 else m,1.4),0.34,-0.2+0.05*k); wet.add(b*BAR+k*BEAT/2,piano(m,1.2),0.22)
    mel=[81,78,76,74,73,76,78,81,86,85,83,81,79,78,76,78,81,83,85,86]
    for k,m in enumerate(mel):
        pn.add(18.0+k*BEAT*2*0.5 if False else 18.0+ (k*1.0), piano(m+0,1.8),0.22,0.25); 
    # S5 soft piano chord stabs on offbeat
    for b in range(14,19):
        for m in chord(b)[1]: pn.add(b*BAR+BEAT*1.5,piano(m+12,1.0),0.10,0.1)
    # RISERS
    for (a,bq,g) in [(0,4,0.35),(8,12,0.45),(26,28,0.35),(36,38,0.45),(38,40,0.5)]:
        r=noise_rise(bq-a); fx.add(a,r,g,0); wet.add(a,r,g*0.4)
    # IMPACTS
    for tb,g in [(4.0,0.9),(12.0,1.0),(38.0,0.7),(40.0,1.0),(46.0,1.1)]:
        b=boom(); fx.add(tb,b,g*0.8,0); wet.add(tb,b,g*0.3)
        c=hp(rng.standard_normal(int(1.6*SR)),4000)*np.exp(-tt(1.6)*3)
        fx.add(tb,c,0.20*g,0)
    # WHOOSH at transitions
    for tb in (10.0,18.0,28.0,38.0):
        w=whoosh(0.9); fx.add(tb-0.45,w,0.25,0); wet.add(tb-0.45,w,0.2)
    # RECORD SCRATCH + bonk
    if include_scratch:
        d=0.42; t=tt(d)
        f=900*np.exp(-t*5.5)+120; ph=2*np.pi*np.cumsum(f)/SR
        x=lp(saw(1,0*t)+0,8000)  # placeholder
        sc=np.sign(np.sin(ph))*0.5+0.5*np.sin(ph)
        n=bp(rng.standard_normal(len(t)),700,5200)
        mod=np.abs(np.sin(2*np.pi*(9+14*t/d)*t))**0.6
        sc=(0.55*sc+0.8*n)*mod*np.exp(-t*3.2)*(1-np.exp(-t*400))
        fx.add(GATE[0],lp(sc,6500),0.42,0)
        t2=tt(0.28); f2=520*np.exp(-t2*4)+140; bonk=np.sin(2*np.pi*np.cumsum(f2)/SR)*np.exp(-t2*10)*(1-np.exp(-t2*200))
        fx.add(6.58,bonk,0.30,0)
    # DUCK (sidechain) for pad/arp/lead in drops
    duck=np.ones(N,np.float32)
    for (a,bq) in (DROP1,DROP2,(30,36)):
        for tb in np.arange(a,bq,BEAT):
            i=int(tb*SR); n=int(0.30*SR)
            duck[i:i+n]*= (1-0.55*np.exp(-np.arange(min(n,N-i))/SR/0.09)).astype(np.float32)
    for b_ in (pad,arp,ld): b_.L*=duck; b_.R*=duck
    # reverb sends
    wl,wr=reverb(wet.L,wet.R,2.4,2.6)
    for b_ in (ld,): wet2=b_
    ldL,ldR=reverb(ld.L*0.5,ld.R*0.5,1.6,3.2)
    delay(ld,0.375,0.38,3)
    # mix
    L=pad.L+arp.L+ld.L+bs.L+dr.L+fx.L+pn.L+wl*0.7+ldR*0.4
    R=pad.R+arp.R+ld.R+bs.R+dr.R+fx.R+pn.R+wr*0.7+ldL*0.4
    # gate music around freeze (everything except fx scratch/bonk): approximate by gating the sum then adding scratch
    return L,R,fx,GATE
if __name__=="__main__":
    L,R,fx,GATE=build()
    # freeze gate
    g=np.ones(N,np.float32); a=int(GATE[0]*SR); b=int(GATE[1]*SR)
    g[a:b]=0; g[a-int(0.02*SR):a]=np.linspace(1,0,int(0.02*SR)); 
    # keep scratch/bonk audible: re-add fx within gate window
    L=L*g; R=R*g
    L[a:b]+=fx.L[a:b]*0.0; 
    # re-add scratch + bonk by rebuilding only those (fx in window contains riser from 0-4? no; 4..10 contains riser at 8 only)
    L[a:b]+=fx.L[a:b]; R[a:b]+=fx.R[a:b]
    # master
    M=np.stack([L,R],1)
    M=hp(M.T,28,2).T
    fi=int(0.5*SR); M[:fi]*=np.linspace(0,1,fi)[:,None]
    fo=int(0.9*SR); M[-fo:]*=np.linspace(1,0,fo)[:,None]**1.5
    pk=np.abs(M).max(); M=M/pk*0.92
    M=np.tanh(M*1.35)/np.tanh(1.35)
    M=M/np.abs(M).max()*0.89
    import wave
    pcm=(M*32767).astype(np.int16)
    with wave.open('/home/claude/build/score.wav','wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print('done',M.shape)
