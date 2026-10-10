import numpy as np, cv2, re, sys, math, subprocess, os, json
HERE=os.path.dirname(os.path.abspath(__file__))
C=json.load(open(os.path.join(HERE,'content.json'),encoding='utf-8'))
from PIL import Image, ImageDraw, ImageFont, ImageFilter, features
W,H=1080,1920; FPS=30; DUR=48.0
ROOT=os.path.join(HERE,'..','assets','photos')+os.sep
LORA='/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf'
LORAI='/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf'
CARL='/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf'
EMOJI='/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
GOLD=(232,190,106); GOLD_HI=(255,228,160); GOLD_LO=(201,150,62); CREAM=(250,243,230)
cl=lambda x,a=0,b=1: max(a,min(b,x))
def A(t,t0,d): return cl((t-t0)/d)
def eo(x): return 1-(1-x)**3
def eio(x): return x*x*(3-2*x)
def eb(x,s=1.7): x=cl(x); return 1+(s+1)*(x-1)**3+s*(x-1)**2
# ---------------- text engine
_fc={}
def font(path,size,wt=None):
    k=(path,size,wt)
    if k not in _fc:
        f=ImageFont.truetype(path,size)
        if wt:
            try: f.set_variation_by_axes([wt])
            except Exception: pass
        _fc[k]=f
    return _fc[k]
RAQM=features.check('raqm')
EMO_RE=re.compile('((?:[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2764][\uFE0F]?(?:\u200D[\U0001F300-\U0001FAFF\u2764][\uFE0F]?)*))')
_ec={}
def emoji_img(e,size):
    k=(e,size)
    if k in _ec: return _ec[k]
    ef=ImageFont.truetype(EMOJI,109)
    c=Image.new('RGBA',(300,160),(0,0,0,0)); d=ImageDraw.Draw(c)
    d.text((10,10),e,font=ef,embedded_color=True)
    bb=c.getbbox(); c=c.crop(bb) if bb else c
    s=size*1.0/109; im=c.resize((max(1,int(c.width*s)),max(1,int(c.height*s))),Image.LANCZOS)
    _ec[k]=im; return im
def split_runs(s):
    return [r for r in EMO_RE.split(s) if r!='']
def run_w(r,f,size,tr):
    if EMO_RE.fullmatch(r): return emoji_img(r,size).width+size*0.08
    return f.getlength(r)+tr*len(r)
def line_w(segs,f,size,tr):
    return sum(run_w(r,f,size,tr) for s,c in segs for r in split_runs(s))
NB=re.compile(r' ((?:[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50\u2764][\uFE0F]?(?:\u200D[\U0001F300-\U0001FAFF\u2764][\uFE0F]?)*)+)$')
def make_text(lines,fpath,size,fill=CREAM,align='center',maxw=None,tr=0,lh=1.2,glow=None,shadow=0.55,grad=None,wt=700,pad=70,fit=None):
    lines=[NB.sub('\u00A0\\1',l) if isinstance(l,str) else l for l in (lines if isinstance(lines,list) else [lines])]
    if fit:
        f0=font(fpath,size,wt if fpath in (LORA,LORAI) else None)
        mw=max(line_w([(l,fill)],f0,size,tr) for l in lines if isinstance(l,str))
        if mw>fit: size=int(size*fit/mw)
    f=font(fpath,size,wt if fpath in (LORA,LORAI) else None)
    L=[]
    for ln in (lines if isinstance(lines,list) else [lines]):
        if isinstance(ln,str):
            if maxw:
                words=ln.split(' '); cur=''
                for w_ in words:
                    t_=(cur+' '+w_).strip()
                    if line_w([(t_,fill)],f,size,tr)<=maxw or not cur: cur=t_
                    else: L.append([(cur,fill)]); cur=w_
                if cur: L.append([(cur,fill)])
            else: L.append([(ln,fill)])
        else: L.append(ln)
    ws=[line_w(s,f,size,tr) for s in L] or [0]; tw=int(max(ws)); th=int(len(L)*size*lh)
    cw,ch=tw+2*pad,th+2*pad+int(size*0.3)
    img=Image.new('RGBA',(cw,ch),(0,0,0,0)); 
    for i,segs in enumerate(L):
        y=pad+int(i*size*lh)
        x=pad+(0 if align=='left' else (tw-ws[i])/2 if align=='center' else tw-ws[i])
        for s,c in segs:
            for r in split_runs(s):
                if EMO_RE.fullmatch(r):
                    e=emoji_img(r,size); img.alpha_composite(e,(int(x),int(y+size*0.12))); x+=e.width+size*0.08
                else:
                    layer=Image.new('RGBA',(cw,ch),(0,0,0,0)); d=ImageDraw.Draw(layer)
                    cx=x
                    if tr:
                        for chh in r: d.text((cx,y),chh,font=f,fill=(255,255,255,255)); cx+=f.getlength(chh)+tr
                    else: d.text((x,y),r,font=f,fill=(255,255,255,255))
                    a=np.array(layer)[...,3:4].astype(np.float32)/255
                    if grad and c==fill:
                        yy=np.linspace(0,1,ch)[:,None,None]; top=np.array(grad[0],np.float32); bot=np.array(grad[1],np.float32)
                        col=top*(1-yy)+bot*yy; col=np.broadcast_to(col,(ch,cw,3))
                    else: col=np.broadcast_to(np.array(c,np.float32),(ch,cw,3))
                    out=np.concatenate([col,a*255],2).astype(np.uint8)
                    img.alpha_composite(Image.fromarray(out,'RGBA'))
                    x+=f.getlength(r)+tr*len(r)
    arr=np.array(img).astype(np.float32); al=arr[...,3]
    base=np.zeros((ch,cw,4),np.float32)
    if shadow:
        sh=cv2.GaussianBlur(al,(0,0),size*0.06+3); sh=np.roll(sh,int(size*0.05),0)
        base[...,3]=np.clip(sh*shadow*1.6,0,255)
    if glow:
        g=cv2.GaussianBlur(al,(0,0),glow[1]); ga=np.clip(g*glow[2],0,255)
        for k in range(3): base[...,k]=np.array(glow[0][k])
        a0=base[...,3]; base[...,3]=a0+ga*(1-a0/255)
        # color of base where only shadow stays black
        m=(ga>a0)[...,None]
        base[...,:3]=np.where(m,np.array(glow[0],np.float32),0)
    # composite text over base
    ta=arr[...,3:4]/255; ba=base[...,3:4]/255
    oa=ta+ba*(1-ta)
    orgb=(arr[...,:3]*ta+base[...,:3]*ba*(1-ta))/np.maximum(oa,1e-4)
    out=np.concatenate([orgb,oa*255],2).clip(0,255).astype(np.uint8)
    return dict(a=out,w=cw,h=ch,tw=tw,pad=pad,size=size)
_tc={}
def T(key,*a,**k):
    if key not in _tc: _tc[key]=make_text(*a,**k)
    return _tc[key]
# ---------------- compositing helpers
def blit(f,s,x,y,a=1.0,mask=None):
    arr=s['a'] if isinstance(s,dict) else s
    h,w=arr.shape[:2]; x=int(round(x)); y=int(round(y))
    x0,y0=max(0,x),max(0,y); x1,y1=min(W,x+w),min(H,y+h)
    if x1<=x0 or y1<=y0 or a<=0.003: return
    sub=arr[y0-y:y1-y,x0-x:x1-x]
    al=sub[...,3:4].astype(np.float32)*(a/255.0)
    if mask is not None: al=al*mask[y0-y:y1-y,x0-x:x1-x,None]
    roi=f[y0:y1,x0:x1]
    roi*=(1-al); roi+=sub[...,:3]*al
def blit_c(f,s,cx,cy,a=1.0,scale=1.0,angle=0.0,mask=None):
    arr=s['a'] if isinstance(s,dict) else s
    if scale==1.0 and angle==0.0: 
        h,w=arr.shape[:2]; blit(f,arr,cx-w/2,cy-h/2,a,mask); return
    h,w=arr.shape[:2]
    M=cv2.getRotationMatrix2D((w/2,h/2),angle,scale)
    cs,sn=abs(M[0,0]),abs(M[0,1]); nw=int(h*sn+w*cs)+2; nh=int(h*cs+w*sn)+2
    M[0,2]+=nw/2-w/2; M[1,2]+=nh/2-h/2
    pm=arr.astype(np.float32); pm[...,:3]*=pm[...,3:4]/255
    wr=cv2.warpAffine(pm,M,(nw,nh),flags=cv2.INTER_LINEAR,borderValue=(0,0,0,0))
    al=wr[...,3:4]; rgb=wr[...,:3]/np.maximum(al/255,1e-4)
    out=np.concatenate([rgb,al],2).clip(0,255).astype(np.uint8)
    blit(f,out,cx-nw/2,cy-nh/2,a,mask)
def reveal(sprite,p,soft=140):
    a=sprite['a'].copy(); h=a.shape[0]
    ys=np.arange(h,dtype=np.float32); edge=p*(h+soft)
    m=np.clip((edge-ys)/soft,0,1); a[...,3]=(a[...,3]*m[:,None]).astype(np.uint8); return a
# ---------------- assets
def load_photo(n):
    im=Image.open(ROOT+n).convert('RGB'); im=im.resize((im.width*3,im.height*3),Image.LANCZOS)
    im=im.filter(ImageFilter.UnsharpMask(3,70,2)); return np.array(im)
P={'goat':load_photo('goat-moment.png'),'car':load_photo('cousin-car.png'),'drink':load_photo('cousin-drink.png')}
def make_bg(img,tint,dark,sat=1.0,extra=(1188,2112)):
    h,w=img.shape[:2]; tw,th=extra; s=max(tw/w,th/h)
    im=cv2.resize(img,(int(w*s),int(h*s)),interpolation=cv2.INTER_AREA)
    y0=(im.shape[0]-th)//2; x0=(im.shape[1]-tw)//2; im=im[y0:y0+th,x0:x0+tw]
    sm=cv2.resize(im,(tw//5,th//5),interpolation=cv2.INTER_AREA); sm=cv2.GaussianBlur(sm,(0,0),14)
    im=cv2.resize(sm,(tw,th),interpolation=cv2.INTER_CUBIC).astype(np.float32)
    g=im.mean(2,keepdims=True); im=g+(im-g)*sat
    im=im*dark+np.array(tint,np.float32); return im.clip(0,255).astype(np.float32)
def base_dark(tint=(0,0,0)):
    ys,xs=np.mgrid[0:210,0:118].astype(np.float32); xs=(xs/118-0.5); ys=(ys/210-0.62)
    r=np.sqrt(xs**2*1.2+ys**2); g=np.clip(1-r*1.6,0,1)**2
    base=np.array([14,13,17],np.float32)+g[...,None]*np.array([58,38,20],np.float32)+np.array(tint,np.float32)
    return cv2.resize(base,(1188,2112),interpolation=cv2.INTER_CUBIC)
BG={'dark':base_dark(),
    'goat':make_bg(P['goat'],(10,6,2),0.42,0.9),
    'car':make_bg(P['car'],(14,9,3),0.55,0.8),
    'drink':make_bg(P['drink'],(16,8,2),0.50,1.0),
    'car_teal':make_bg(P['car'],(0,6,10),0.40,0.6)}
def bg_crop(name,t,amp=36,spd=0.25):
    ox=int(54+math.sin(t*spd)*amp); oy=int(96+math.cos(t*spd*0.8)*amp*1.2)
    return BG[name][oy:oy+H,ox:ox+W].copy()
# vignette + grain
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
VIG=(1-0.62*np.clip(np.sqrt(((xx/W-0.5)/0.72)**2+((yy/H-0.5)/0.80)**2),0,1.4)**2.6)[...,None].astype(np.float32); del yy,xx
rg=np.random.default_rng(5); GRAIN=[cv2.resize(rg.standard_normal((H//3,W//3)).astype(np.float32)*3.6,(W,H))[...,None] for _ in range(6)]
# dust sprites
def dot(r):
    n=int(r*3)|1; y,x=np.mgrid[-(n//2):n//2+1,-(n//2):n//2+1].astype(np.float32); return np.exp(-(x*x+y*y)/(2*(r*0.5)**2))[...,None]
DOT={r:dot(r) for r in range(2,14)}
def disc(r):
    n=int(r*2+10); y,x=np.mgrid[-(n//2):n//2+1,-(n//2):n//2+1].astype(np.float32); d=np.sqrt(x*x+y*y)
    return (np.clip(1-(d-r+2)/3.0,0,1)*0.6+np.exp(-(d/r)**2)*0.1)[...,None]
class Dust:
    def __init__(s,n,seed,col=GOLD,speed=26,bright=1.0,rmin=2,rmax=7):
        r=np.random.default_rng(seed); s.n=n; s.x=r.uniform(0,W,n); s.y=r.uniform(0,H,n); s.d=r.uniform(0.3,1,n)
        s.ph=r.uniform(0,6.28,n); s.w=r.uniform(0.3,1.2,n); s.col=np.array(col,np.float32); s.sp=speed; s.b=bright
        s.r=(rmin+(rmax-rmin)*s.d**1.5).astype(int)
    def draw(s,f,t,a=1.0):
        for i in range(s.n):
            x=(s.x[i]+math.sin(t*s.w[i]+s.ph[i])*22*s.d[i])%W; y=(s.y[i]-s.sp*s.d[i]*t)%H
            tw=0.55+0.45*math.sin(t*(1.5+s.w[i]*2)+s.ph[i]); sp=DOT[int(s.r[i])]; n=sp.shape[0]
            x0=int(x-n//2); y0=int(y-n//2)
            if x0<0 or y0<0 or x0+n>W or y0+n>H: continue
            f[y0:y0+n,x0:x0+n]+=sp*s.col*(s.b*a*tw*(0.5+s.d[i]*0.9))
class Bokeh:
    def __init__(s,n,seed,col=(255,176,92),sp=14):
        r=np.random.default_rng(seed); s.n=n; s.x=r.uniform(0,W,n); s.y=r.uniform(0,H,n); s.r=r.integers(26,80,n); s.ph=r.uniform(0,6.28,n); s.col=np.array(col,np.float32); s.sp=sp
        s.s={int(k):disc(int(k)) for k in set(s.r)}
    def draw(s,f,t,a=1.0):
        for i in range(s.n):
            x=s.x[i]+math.sin(t*0.3+s.ph[i])*30; y=(s.y[i]-s.sp*t*(0.4+s.r[i]/80))%H
            sp=s.s[int(s.r[i])]; n=sp.shape[0]; x0=int(x-n/2); y0=int(y-n/2)
            if x0<0 or y0<0 or x0+n>W or y0+n>H: continue
            f[y0:y0+n,x0:x0+n]+=sp*s.col*(0.20*a*(0.6+0.4*math.sin(t*0.9+s.ph[i])))
LEAK=None
_lk={}
def make_leak():
    ys,xs=np.mgrid[0:240,0:135].astype(np.float32); xs/=135; ys/=240
    l=np.clip(1-np.sqrt((xs-0.0)**2*1.3+(ys-0.35)**2*0.5)*1.6,0,1)**2
    r=np.clip(1-np.sqrt((xs-1.05)**2*1.3+(ys-0.8)**2*0.5)*1.7,0,1)**2
    return l.astype(np.float32),r.astype(np.float32)
LK=make_leak()
def leak(f,a,side='L',col=(255,150,60)):
    if a<=0.01: return
    if side not in _lk: _lk[side]=cv2.resize(LK[0] if side=='L' else LK[1],(W,H),interpolation=cv2.INTER_LINEAR)[...,None]
    f+=_lk[side]*(np.array(col,np.float32)*a)
# god rays
th_g,r_g=None,None
def rays(f,t,a,cx=0.5,cy=0.38,col=(255,205,120)):
    global th_g,r_g
    if th_g is None:
        ys,xs=np.mgrid[0:240,0:135].astype(np.float32); xs=(xs/135-cx)*0.5625; ys=(ys/240-cy)
        th_g=np.arctan2(ys,xs); r_g=np.sqrt(xs**2+ys**2)
    m=(0.5+0.5*np.cos(th_g*11+t*0.35))**4*np.clip(1-r_g*1.5,0,1)
    m=cv2.resize(m.astype(np.float32),(W,H),interpolation=cv2.INTER_LINEAR)
    f+=m[...,None]*np.array(col,np.float32)*a
_rc={}
def radial(f,cx,cy,r,col,a):
    r=int(round(r/20)*20) or 20; n=int(r*2); x0,y0=int(cx-r),int(cy-r)
    if r not in _rc:
        y,x=np.mgrid[0:n,0:n].astype(np.float32); d=np.sqrt((x-r)**2+(y-r)**2)/r; _rc[r]=np.clip(1-d,0,1)**2.2
    g=_rc[r]
    X0,Y0,X1,Y1=max(0,x0),max(0,y0),min(W,x0+n),min(H,y0+n)
    if X1<=X0 or Y1<=Y0: return
    f[Y0:Y1,X0:X1]+=g[Y0-y0:Y1-y0,X0-x0:X1-x0,None]*np.array(col,np.float32)*a
# ---------------- photo card
_cm={}
def card_masks(cw,ch,r,b):
    k=(cw,ch,r,b)
    if k in _cm: return _cm[k]
    ow,oh=cw+2*b,ch+2*b
    def rr(w,h,rad,off):
        m=np.zeros((oh,ow),np.uint8); cv2.rectangle(m,(off+rad,off),(off+w-rad,off+h),255,-1); cv2.rectangle(m,(off,off+rad),(off+w,off+h-rad),255,-1)
        for cx_,cy_ in [(off+rad,off+rad),(off+w-rad,off+rad),(off+rad,off+h-rad),(off+w-rad,off+h-rad)]: cv2.circle(m,(cx_,cy_),rad,255,-1,cv2.LINE_AA)
        return m
    outer=rr(cw+2*b,ch+2*b,r+b,0).astype(np.float32)/255; inner=rr(cw,ch,r,b).astype(np.float32)/255
    # shadow
    pad=90; sh=np.zeros((oh+2*pad,ow+2*pad),np.float32); sh[pad:pad+oh,pad:pad+ow]=outer; sh=cv2.GaussianBlur(sh,(0,0),34)
    yy_,xx_=np.mgrid[0:ch,0:cw].astype(np.float32); diag=(xx_/cw*0.55+yy_/ch*0.85)
    _cm[k]=(outer,inner,sh,diag); return _cm[k]
def make_card(name,cw,ch,zoom=1.0,cx=0.5,cy=0.5,sheen=-1,sat=1.0,bright=1.0,b=4,r=28,contrast=1.0):
    img=P[name]; h,w=img.shape[:2]
    bw=min(w,h*cw/ch); bh=bw*ch/cw; vw=bw/zoom; vh=bh/zoom
    x0=np.clip(cx*w-vw/2,0,w-vw); y0=np.clip(cy*h-vh/2,0,h-vh)
    M=np.float32([[cw/vw,0,-x0*cw/vw],[0,ch/vh,-y0*ch/vh]])
    ph=cv2.warpAffine(img,M,(cw,ch),flags=cv2.INTER_LINEAR).astype(np.float32)
    outer,inner,sh,diag=card_masks(cw,ch,r,b)
    if sat!=1.0: g=ph.mean(2,keepdims=True); ph=g+(ph-g)*sat
    if contrast!=1.0: ph=(ph-128)*contrast+128
    ph*=bright
    if sheen>=0:
        pos=-0.3+sheen*1.6; band=np.exp(-((diag-pos)/0.07)**2)*60; ph+=band[...,None]*np.array([1,0.93,0.8],np.float32)
    ow,oh=cw+2*b,ch+2*b
    full=np.zeros((oh,ow,3),np.float32); full[b:b+ch,b:b+cw]=ph
    ring=np.clip(outer-inner,0,1)[...,None]
    gold=np.array(GOLD,np.float32)
    rgb=full*inner[...,None]+gold*ring
    a=np.clip(outer,0,1)*255
    return np.concatenate([rgb.clip(0,255),a[...,None]],2).astype(np.uint8),sh
def draw_card(f,name,cx,cy,cw,ch,zoom=1.0,fx=0.5,fy=0.5,angle=0.0,scale=1.0,a=1.0,sheen=-1,sat=1.0,bright=1.0,glow=0.0,shadow=True,contrast=1.0):
    spr,sh=make_card(name,cw,ch,zoom,fx,fy,sheen,sat,bright,contrast=contrast)
    if glow>0: radial(f,cx,cy+20,max(cw,ch)*0.85*scale,(255,190,100),glow*a)
    if shadow:
        k=(cw,ch)
        if k not in _ss: _ss[k]={'a':np.dstack([np.zeros_like(sh)]*3+[sh*210*0.8]).astype(np.uint8)}
        blit_c(f,_ss[k],cx+10,cy+34,a*0.9,scale,angle)
    blit_c(f,spr,cx,cy,a,scale,angle)
_ss={}
# ---------------- confetti
CONF_COL=[(255,214,128),(250,243,230),(232,190,106),(255,150,110),(255,236,190),(160,200,255)]
class Confetti:
    def __init__(s,t0,origins,n=130,seed=1,life=4.2,power=1.0):
        r=np.random.default_rng(seed); s.t0=t0; s.life=life; s.items=[]
        for i in range(n):
            ox,oy,ang0,spread=origins[i%len(origins)]
            ang=math.radians(ang0+r.uniform(-spread,spread)); v=r.uniform(900,2300)*power
            s.items.append(dict(x=ox,y=oy,vx=math.cos(ang)*v,vy=-math.sin(ang)*v,w=r.uniform(14,30),h=r.uniform(8,16),rot=r.uniform(0,6.28),rs=r.uniform(-9,9),fl=r.uniform(3,9),ph=r.uniform(0,6.28),c=CONF_COL[int(r.integers(len(CONF_COL)))],dr=r.uniform(1.8,3.2)))
    def draw(s,f,t):
        u=t-s.t0
        if u<0 or u>s.life: return
        fade=1.0 if u<s.life-0.9 else (s.life-u)/0.9
        for it in s.items:
            k=it['dr']; e=(1-math.exp(-k*u))/k
            x=it['x']+it['vx']*e; y=it['y']+it['vy']*e+0.5*1500*u*u*0.55+60*u
            if y>H+60 or x<-60 or x>W+60: continue
            rot=it['rot']+it['rs']*u; sq=abs(math.cos(it['ph']+it['fl']*u))
            w,h=it['w'],it['h']*max(sq,0.15)
            c,sn=math.cos(rot),math.sin(rot)
            pts=np.array([[x+(-w*c+h*sn)/2,y+(-w*sn-h*c)/2],[x+(w*c+h*sn)/2,y+(w*sn-h*c)/2],[x+(w*c-h*sn)/2,y+(w*sn+h*c)/2],[x+(-w*c-h*sn)/2,y+(-w*sn+h*c)/2]],np.int32)
            col=tuple(float(v*(0.75+0.25*sq)) for v in it['c'])
            if fade>=0.99: cv2.fillConvexPoly(f,pts,col,cv2.LINE_AA)
            else:
                ov=f.copy(); cv2.fillConvexPoly(ov,pts,col,cv2.LINE_AA); x0=max(0,int(x-40)); x1=min(W,int(x+40)); y0=max(0,int(y-40)); y1=min(H,int(y+40))
                f[y0:y1,x0:x1]=f[y0:y1,x0:x1]*(1-fade)+ov[y0:y1,x0:x1]*fade
CONF=[Confetti(12.0,[(-20,H+20,62,22),(W+20,H+20,118,22)],150,3,4.4),
      Confetti(40.0,[(-20,H+20,64,22),(W+20,H+20,116,22),(W/2,H+40,90,30)],170,7,4.6),
      Confetti(46.0,[(-20,H*0.55,35,25),(W+20,H*0.55,145,25),(W/2,H+40,90,40)],230,11,4.8,1.1)]
# ---------------- scenes
DUST1=Dust(70,1,GOLD,22,1.0); DUST2=Dust(60,2,GOLD,30,1.0); DUST3=Dust(80,3,GOLD_HI,34,1.1); DUST4=Dust(40,4,(255,200,140),14,0.8,3,9)
DUST5=Dust(50,5,GOLD,18,0.8); DUST6=Dust(90,6,GOLD_HI,40,1.1)
BOK4=Bokeh(14,9); BOK5=Bokeh(10,10,(150,185,255),10); BOK2=Bokeh(8,11,(255,170,90),12); BOK3=Bokeh(10,12,(255,185,100),16); BOK6=Bokeh(12,13,(255,190,110),16)
def beat_pulse(t,t0,amp=0.014,bpm=120):
    if t<t0: return 1.0
    ph=((t-t0)%(60/bpm))/(60/bpm); return 1+amp*(1-ph)**3
def left_x(s): return 90-s['pad']
def scene1(t):
    f=bg_crop('dark',t,10,0.2); u=t
    radial(f,540,1500,900,(120,70,25),0.55*A(u,0,1.5)*(0.8+0.2*math.sin(u*3)))
    # siren glow
    if u>1.0:
        k=abs(math.sin((u-1.0)*math.pi*1.5)); radial(f,140,300,700,(255,40,20),0.30*k*A(u,1.0,0.3)); radial(f,940,300,700,(255,40,20),0.30*(1-k)*A(u,1.0,0.3))
    DUST1.draw(f,u,A(u,0,0.8))
    # ghost 13
    g=T('ghost13',[ '13'],LORA,880,fill=GOLD,wt=800,pad=40,shadow=0,glow=((255,190,90),20,0.8))
    a=g['a'].copy(); rgb=a[...,:3]; 
    sc=1.0+0.10*(u/4)+0.0
    fa=A(u,0.3,1.4)*0.0+0.10*A(u,0.2,1.6)
    mask_ring=np.array(Image.fromarray(a[...,3]).filter(ImageFilter.MinFilter(9)))
    ring=np.clip(a[...,3].astype(np.int16)-mask_ring.astype(np.int16),0,255).astype(np.uint8)
    ghost=np.dstack([np.full(ring.shape,232,np.uint8),np.full(ring.shape,190,np.uint8),np.full(ring.shape,106,np.uint8),ring])
    blit_c(f,ghost,540,760,fa*5.0,sc)
    # lines
    lw=int(820*eo(A(u,0.5,1.0))); 
    if lw>2:
        f[868:870,540-lw//2:540+lw//2]=f[868:870,540-lw//2:540+lw//2]*0.3+np.array(GOLD)*0.7
    bn=T('breaking',[C['breaking']],CARL,78,fill=GOLD,tr=14,glow=((255,190,90),16,0.7),grad=(GOLD_HI,GOLD_LO))
    si=T('siren',['🚨'],CARL,92,pad=30,shadow=0.4)
    p=eo(A(u,1.0,0.5)); flick=1.0 if u>1.5 else (0.4+0.6*(math.sin(u*70)>0))
    blit_c(f,bn,610,930+(1-p)*24,p*flick); blit_c(f,si,196,925+(1-p)*24,p*flick)
    for i,(txt,t0) in enumerate([(C['apna'],2.35),('turns',2.75),(C['today'],3.15)]):
        p=eo(A(u,t0,0.4)); y=1130+i*190
        if i==1:
            s1=T('turns',[C['turns']+' '],LORA,150,fill=CREAM); s2=T('n13',[C['s1_num']],LORA,170,fill=GOLD,grad=(GOLD_HI,GOLD_LO),glow=((255,190,90),22,0.8))
            tot=s1['tw']+s2['tw']; x=540-tot/2
            blit(f,s1,x-s1['pad'],y-s1['h']/2+(1-p)*40,p); blit(f,s2,x+s1['tw']-s2['pad']-8,y-s2['h']/2+(1-p)*40-8,p*1.0)
        else:
            s=T('l1_'+txt,[txt],LORA,150,fill=CREAM); blit_c(f,s,540,y+(1-p)*40,p)
    # build-up whiteout
    w=eio(A(u,3.55,0.45)); f+=255*w*0.9
    return f
def scene2(t):
    u=t-4.0; f=bg_crop('goat',t,30)
    leak(f,0.22+0.0,'L'); BOK2.draw(f,t,0.9); DUST2.draw(f,t,1.0)
    frz=2.0<=u<3.0
    pp=eb(A(u,0,0.55)); sc=0.98*(1.28-0.28*pp) if u<0.55 else 0.98
    zoom=1.0+0.07*A(u,0,2.0)+ (0.05*A(u,3.0,3.0) if u>=3.0 else 0)
    fx,fy=0.5,0.62
    if frz:
        k=eo(A(u,2.0,0.10)); zoom=1.07+0.32*k; fx=0.5+0.12*k; fy=0.62+0.02*k
    ang=-2.5+ (0 if frz else math.sin(u*1.3)*0.4)
    a=eo(A(u,0,0.25))
    draw_card(f,'goat',455,720,720,960,zoom,fx,fy,ang,sc*(1.012 if frz else 1.0),a,sheen=A(u,0.3,1.2) if u<1.6 else -1,sat=(0.55 if frz else 1.0),contrast=(1.12 if frz else 1.0),glow=0.35)
    if frz:
        # viewfinder brackets + tag
        c=np.array(CREAM,np.float32); L=70; x0,y0,x1,y1=108,236,806,1204
        for (cx,cy,dx,dy) in [(x0,y0,1,1),(x1,y0,-1,1),(x0,y1,1,-1),(x1,y1,-1,-1)]:
            xa,xb=sorted([cx,cx+dx*L]); ya,yb=sorted([cy,cy+dy*4]); f[ya:yb,xa:xb]=c
            xa,xb=sorted([cx,cx+dx*4]); ya,yb=sorted([cy,cy+dy*L]); f[ya:yb,xa:xb]=c
        tag=T('frz',[C['freeze']],CARL,38,fill=CREAM,tr=6,pad=20,shadow=0.5)
        blit_c(f,tag,330,285,0.95)
    s1=T('s2a',[C['s2a']],LORAI,70,fill=GOLD_HI,align='left',grad=(GOLD_HI,GOLD),wt=500)
    p=eo(A(u,0.7,0.5)); blit(f,s1,left_x(s1),1260+(1-p)*30,p)
    s2=T('s2b',C['s2b'],LORA,82,fill=CREAM,align='left',maxw=860,lh=1.16)
    p=eb(A(u,3.0,0.35)); a2=eo(A(u,3.0,0.15))
    if u>=3.0: blit_c(f,s2,90-s2['pad']+s2['w']/2,1395+s2['h']/2+(1-a2)*10,a2,0.9+0.1*p)
    return f
def scene3(t):
    u=t-10.0; f=bg_crop('car',t,30)
    leak(f,0.30,'R'); BOK3.draw(f,t,0.9)
    drop=t>=12.0
    if drop: rays(f,t,0.16*eo(A(t,12,0.6)))
    DUST3.draw(f,t,1.0)
    # divider + vertical label
    h=int(1100*eo(A(u,0.2,0.9)))
    if h>2: f[190:190+h,264:267]=f[190:190+h,264:267]*0.25+np.array(GOLD)*0.75
    vt=T('vert',[C['vert']],CARL,46,fill=GOLD,tr=16,pad=24); v=np.rot90(vt['a'],1).copy()
    blit_c(f,v,160,740,0.85*A(u,0.6,0.6))
    p=eo(A(u,0.15,0.8)); zoom=1.0+0.07*A(u,0,8)
    pul=beat_pulse(t,12.0,0.016) if drop else 1.0
    cxp=650+(1-p)*420
    draw_card(f,'car',cxp,740,700,930,zoom,0.5,0.5,0.0,pul,p,sheen=A(t,12.0,1.0) if drop else A(u,0.5,1.5)*0.9,glow=(0.55 if drop else 0.25))
    # text
    if u<2.0:
        s=T('s3a',[C['s3a']],LORAI,78,fill=GOLD_HI,align='left',maxw=860,grad=(GOLD_HI,GOLD),wt=500)
        p=eo(A(u,0.5,0.5)); out=1-A(u,1.82,0.18); blit(f,s,left_x(s),1370+(1-p)*30,p*out)
    else:
        v=u-2.0
        lines=[(C['s3_0'],112,GOLD_HI,(GOLD_HI,GOLD_LO)),(C['s3_1'],168,CREAM,None),(C['s3_2'],150,GOLD_HI,(GOLD_HI,GOLD_LO))]
        y=1262
        for i,(txt,sz,col,gr) in enumerate(lines):
            s=T('s3_%d'%i,[txt],LORA,sz,fill=col,align='left',grad=gr,glow=((255,190,90),18,0.55) if gr else None,wt=800,lh=1.0)
            q=A(v,i*0.12,0.18); sc=1+0.35*(1-eb(A(v,i*0.12,0.35),2.2)); 
            blit_c(f,s,90-s['pad']+s['w']/2,y+s['h']/2,eo(q),sc)
            y+=int(sz*1.06)+ (10 if i==0 else 0)
    return f
def scene4(t):
    u=t-18.0; f=bg_crop('drink',t,24,0.18)
    leak(f,0.28,'L',(255,170,90)); BOK4.draw(f,t,1.3); DUST4.draw(f,t,1.0)
    p=eo(A(u,0.1,1.1)); zoom=1.0+0.11*A(u,0,10); fx=0.5+0.04*A(u,0,10); fy=0.56
    by=math.sin(u*0.7)*10
    draw_card(f,'drink',540,700+by,800,1000,zoom,fx,fy,0.0,0.94+0.06*p,p,sheen=A(u,0.8,2.0)*0.95,glow=0.40,bright=1.02)
    s1=T('s4a',[C['s4a']],LORAI,70,fill=CREAM,align='left',maxw=900,wt=500,lh=1.2)
    p1=A(u,0.9,1.4)
    if p1>0: blit(f,reveal(s1,eio(p1)),left_x(s1),1290,1.0)
    s2=T('s4b',[C['s4b']],LORA,56,fill=GOLD_HI,align='left',maxw=900,wt=500,lh=1.2)
    p2=A(u,5.2,1.3)
    if p2>0: blit(f,reveal(s2,eio(p2)),left_x(s2),1610,1.0)
    return f
def scene5(t):
    u=t-28.0; f=bg_crop('car_teal',t,22,0.15)
    BOK5.draw(f,t,1.0); leak(f,0.16,'R',(255,170,80)); DUST5.draw(f,t,1.0)
    # left gold rule
    h=int(1180*eo(A(u,0.1,1.2)))
    if h>2: f[300:300+h,86:89]=f[300:300+h,86:89]*0.2+np.array(GOLD)*0.8
    a=T('s5a',[C['s5a']],LORAI,66,fill=CREAM,align='left',wt=500)
    p=eo(A(u,0.4,0.6)); blit(f,a,126-a['pad'],320+(1-p)*28,p)
    b=T('s5b',[C['s5b']],LORA,150,fill=GOLD_HI,align='left',fit=830,grad=(GOLD_HI,GOLD_LO),glow=((255,190,90),24,0.5),wt=800,lh=1.0)
    p=eo(A(u,0.8,0.7)); blit(f,b,126-b['pad'],405+(1-p)*34,p)
    c=T('s5c',[C['s5c']],LORA,62,fill=CREAM,align='left',maxw=830,wt=500,lh=1.28)
    p=A(u,1.8,1.6)
    if p>0: blit(f,reveal(c,eio(p)),126-c['pad'],760,1.0)
    d=T('s5d',[C['s5d']],LORAI,66,fill=GOLD_HI,align='left',maxw=830,wt=500,lh=1.26)
    p=A(u,5.6,1.5)
    if p>0: blit(f,reveal(d,eio(p)),126-d['pad'],1290,1.0)
    return f
def scene6(t):
    u=t-38.0; f=bg_crop('goat',t,26,0.2)
    leak(f,0.24,'L'); BOK6.draw(f,t,1.0); 
    if t>=40.0: rays(f,t,0.15*eo(A(t,40,0.8)),0.5,0.30)
    DUST6.draw(f,t,1.0)
    pul=beat_pulse(t,40.0,0.014) if 40<=t<46 else 1.0
    items=[('car',270,640,440,587,-9.0,0.30),('goat',810,640,440,587,9.0,0.45),('drink',540,600,580,725,0.0,0.60)]
    for nme,cx,cy,cw,ch,ang,t0 in items:
        p=eb(A(u,t0,0.7)); a=eo(A(u,t0,0.3))
        fl=math.sin(u*1.1+cx)*8
        draw_card(f,nme,cx,cy+(1-p)*260+fl,cw,ch,1.0+0.03*A(u,0,10),0.5,0.5 if nme!='goat' else 0.62,ang*(0.6+0.4*p)+math.sin(u*0.8+cx)*0.5,pul*(0.86+0.14*p),a,glow=0.0,sheen=-1)
    base=1235
    segs=[(0.4,3.6,'a'),(3.6,5.9,'b'),(5.9,8.0,'c')]
    def show(key,t0,t1):
        if not (t0<=u<t1): return 0,0
        return eo(A(u,t0,0.3))*(1-A(u,t1-0.2,0.2)), eb(A(u,t0,0.4),2.0)
    sa=T('s6a',[C['s6a']],LORA,86,fill=CREAM,align='center',fit=900,wt=700,lh=1.15)
    a,q=show('a',0.4,3.6); blit_c(f,sa,540,base+160+(1-q)*40,a)
    sb=T('s6b',C['s6b'],LORAI,74,fill=GOLD_HI,align='center',maxw=900,wt=500,lh=1.2,grad=(GOLD_HI,GOLD))
    a,q=show('b',3.6,5.9); blit_c(f,sb,540,base+170+(1-q)*40,a)
    sc=T('s6c',[[(C['s6c1'],CREAM),(C['s6c_hl'],GOLD_HI),(C['s6c2'],CREAM)],[(C['s6c3'],CREAM)]],LORA,80,fill=CREAM,align='center',wt=700,lh=1.2)
    a,q=show('c',5.9,8.0); blit_c(f,sc,540,base+170+(1-q)*40,a)
    if u>=8.0:
        fin=T('s6d',C['s6d'],LORA,150,fill=GOLD_HI,align='center',fit=900,wt=800,lh=1.02,grad=(GOLD_HI,GOLD_LO),glow=((255,190,90),26,0.7))
        v=u-8.0; sc_=1+0.45*(1-eb(A(v,0,0.45),2.0)); blit_c(f,fin,540,base+205,eo(A(v,0,0.12)),sc_*(1+0.012*math.sin(v*5)))
    return f
SCENES=[(0.0,4.0,scene1),(4.0,10.0,scene2),(10.0,18.0,scene3),(18.0,28.0,scene4),(28.0,38.0,scene5),(38.0,48.0,scene6)]
# ---------------- transitions
def vblur(f,k):
    k=int(k)|1
    return cv2.blur(f,(1,k)) if k>2 else f
def transition(idx,t,fa,fb):
    # idx: boundary index (1..5)
    T0=SCENES[idx][0]
    if idx==1: return None
    if idx==2:  # whip pan up
        p=eio(A(t,T0-0.28,0.56)); sp=math.sin(p*math.pi); out=np.empty_like(fa); dy=int(p*H)
        a=np.roll(fa,-dy,0); b=np.roll(fb,H-dy,0)
        m=np.zeros((H,1,1),np.float32); m[:H-dy]=1
        out=a*m+b*(1-m); return vblur(out,sp*70)
    if idx==3:  # warm flash dissolve
        p=eio(A(t,T0-0.45,0.9)); out=fa*(1-p)+fb*p; k=math.sin(p*math.pi)
        leak(out,0.9*k,'L',(255,165,70)); leak(out,0.7*k,'R',(255,190,110)); return out
    if idx==4:  # dip to dark
        p=A(t,T0-0.5,1.0); 
        if p<0.5: return fa*(1-eio(p*2))*1.0+0
        return fb*eio((p-0.5)*2)
    if idx==5:  # zoom through
        p=eio(A(t,T0-0.3,0.6)); 
        if p<0.5:
            s=1+0.5*(p*2)**2; M=cv2.getRotationMatrix2D((W/2,H/2),0,s); return cv2.warpAffine(fa,M,(W,H),flags=cv2.INTER_LINEAR)*(1-(p*2)**2*0.6)+255*(p*2)**3*0.5
        q=(p-0.5)*2; s=1.35-0.35*q; M=cv2.getRotationMatrix2D((W/2,H/2),0,s); return cv2.warpAffine(fb,M,(W,H),flags=cv2.INTER_LINEAR)*(0.4+0.6*q)+255*(1-q)**3*0.5
HALF={2:0.28,3:0.45,4:0.5,5:0.3}
def post(f,t):
    # confetti
    for c in CONF: c.draw(f,t)
    # shake
    sh=[(4.0,16,0.45),(12.0,18,0.55),(40.0,16,0.5),(46.0,20,0.6),(6.0,6,0.2)]
    dx=dy=0.0; ca=0.0
    for t0,amp,d in sh:
        if t0<=t<t0+d:
            k=(1-(t-t0)/d)**2; dx+=amp*k*math.sin((t-t0)*95); dy+=amp*k*math.cos((t-t0)*83); ca=max(ca,k)
    if abs(dx)+abs(dy)>0.2:
        f=cv2.warpAffine(f,np.float32([[1,0,dx],[0,1,dy]]),(W,H),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
    if ca>0.05:
        d=int(8*ca); f[...,0]=np.roll(f[...,0],d,1); f[...,2]=np.roll(f[...,2],-d,1)
    f*=VIG
    f+=GRAIN[int(t*FPS)%6]
    fl=0.0
    for t0,amp,d in [(4.0,1.0,0.35),(12.0,0.85,0.4),(6.0,0.30,0.12),(38.0,0.5,0.3),(40.0,0.75,0.4),(46.0,1.0,0.55)]:
        if t0<=t<t0+d: fl=max(fl,amp*(1-(t-t0)/d)**2)
    if fl>0.01: f+=255*fl*0.8
    return np.clip(f,0,255).astype(np.uint8)
def sc_index(t):
    for i,(a,b,fn) in enumerate(SCENES):
        if a<=t<b: return i
    return len(SCENES)-1
def render(t):
    i=sc_index(t); fn=SCENES[i][2]
    f=None
    for idx in HALF:
        T0=SCENES[idx][0]
        if T0-HALF[idx]<=t<T0+HALF[idx]:
            fa=SCENES[idx-1][2](t); fb=SCENES[idx][2](t); f=transition(idx,t,fa,fb); break
    if f is None: f=fn(t)
    return post(f.astype(np.float32),t)
if __name__=='__main__':
    # python render_video.py            -> builds ../assets/video/birthday-video.mp4 (video + soundtrack)
    # python render_video.py stills DIR 5.0 13.0   -> saves preview frames to DIR
    mode=sys.argv[1] if len(sys.argv)>1 else 'build'
    if mode=='stills':
        out=sys.argv[2]; os.makedirs(out,exist_ok=True)
        for tt_ in [float(x) for x in sys.argv[3:]]:
            Image.fromarray(render(tt_)).save(os.path.join(out,f'frame_{tt_:06.2f}.png')); print('saved',tt_,flush=True)
    elif mode=='build':
        final=os.path.join(HERE,'..','assets','video','birthday-video.mp4')
        os.makedirs(os.path.dirname(final),exist_ok=True)
        silent=os.path.join(HERE,'_silent.mp4')
        a,b=0,int(round(DUR*FPS))
        cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','25','-maxrate','2200k','-bufsize','4400k','-g','60','-pix_fmt','yuv420p','-profile:v','high','-level','4.1',silent]
        pr=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        for n in range(a,b):
            pr.stdin.write(render(n/FPS).tobytes())
            if n%150==0: print('frame',n,'/',b,flush=True)
        pr.stdin.close(); pr.wait()
        subprocess.run(['ffmpeg','-y','-v','error','-i',silent,'-i',os.path.join(HERE,'soundtrack.m4a'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','160k','-t',str(DUR),'-movflags','+faststart',final],check=True)
        os.remove(silent); print('built',os.path.abspath(final),flush=True)
    else:
        raise SystemExit('unknown mode')
