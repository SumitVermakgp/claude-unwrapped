#!/usr/bin/env python3
"""
Claude Unwrapped by RAIL
=========================
Your year with Claude, in numbers.

Usage:
  python3 claude_unwrapped.py                          # Interactive
  python3 claude_unwrapped.py export1.zip export2.zip  # With exports

Requirements: Python 3.8+, no external dependencies.
"""

import json,os,sys,glob,shutil,zipfile,argparse,tempfile,fnmatch,re
from datetime import datetime,timedelta
from collections import defaultdict,Counter

# ============================================================================
# CONFIG
# ============================================================================

B={"tl":"#75BFAF","td":"#2D6B5A","bg":"#0c0f13","sf":"#111418",
   "bd":"#1c2028","tx":"#e8e8ec","mt":"#6a6a78","rd":"#fb7185",
   "am":"#fbbf24","gn":"#22c55e","bl":"#38bdf8"}

FRUST=["wrong","bad","useless","shit","buggy","broken","not working",
       "terrible","annoyed","frustrat","waste","fix this","hell",
       "so bad","why your","doesnt work","doesn't work","ugh",
       "deleted","mess up","crap","pathetic","stupid","hate","awful",
       "horrible","trash","worst","garbage","sucks"]
POS=["thank","perfect","great","good","yes","nice","exactly","cool",
     "awesome","love it","well done","impressive","excellent","amazing"]
APOL=["my bad","i apologize","i'm sorry","my mistake","you're right","you're absolutely right"]
RESTART=["start from 0","start from zero","start over","from scratch",
         "redo everything","rebuild","clean slate","nuke it","throw away",
         "scrap it","forget everything","begin again"]
SPEECH=["um,","uh,","like,","you know,","i mean,","basically,",
        "so basically","i'm yeah","not sure if my voice"]

# ============================================================================
# HELPERS
# ============================================================================

def szf(n):
    for u in("B","KB","MB","GB"):
        if abs(n)<1024: return f"{n:3.1f} {u}"
        n/=1024
    return f"{n:.1f} TB"

def sjl(p):
    try:
        with open(p,"r",encoding="utf-8") as f: return json.load(f)
    except: return None

def dsz(p):
    t=0
    for dp,_,fs in os.walk(p):
        for f in fs:
            try: t+=os.path.getsize(os.path.join(dp,f))
            except: pass
    return t

def ff(b,pat):
    r=[]
    for dp,_,fs in os.walk(b):
        for f in fs:
            if fnmatch.fnmatch(f,pat): r.append(os.path.join(dp,f))
    return r

def step(m): print(f"  \033[36m>\033[0m {m}")
def hdr(m): print(f"\n\033[1;97m{'='*60}\033[0m\n  \033[1;97m{m}\033[0m\n\033[1;97m{'='*60}\033[0m\n")
def wrn(m): print(f"  \033[33m!\033[0m {m}")
def ok(m): print(f"  \033[32m+\033[0m {m}")
def esc(s): return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def ask_yn(p):
    while True:
        r=input(f"  \033[36m?\033[0m {p} [y/n]: ").strip().lower()
        if r in("y","yes"): return True
        if r in("n","no"): return False

def ask_path(p):
    r=input(f"  \033[36m?\033[0m {p}: ").strip().strip('"').strip("'")
    return os.path.expanduser(r) if r else ""

def gtx(msg):
    t=""
    for p in msg.get("content",[]):
        if isinstance(p,dict) and p.get("type")=="text": t+=p.get("text","")
    return t

# ============================================================================
# CLAUDE CODE SCANNER
# ============================================================================

def scan_cc(cd):
    step(f"Scanning {cd}")
    d={"found":False,"size":0,"sessions":0,"messages":0,"first":"",
       "longest_h":0,"models":{},"daily":[],"plugins":[],"projects":[],
       "perms":0,"todos":0,"tasks":0,"plans":0,"versions":[]}
    if not os.path.isdir(cd): wrn(f"Not found: {cd}"); return d
    d["found"]=True; d["size"]=dsz(cd); ok(f"Found: {szf(d['size'])}")
    st=sjl(os.path.join(cd,"stats-cache.json")) or {}
    if st:
        d["sessions"]=st.get("totalSessions",0); d["messages"]=st.get("totalMessages",0)
        d["first"]=st.get("firstSessionDate","")
        d["longest_h"]=st.get("longestSession",{}).get("duration",0)/3600000
        d["models"]=st.get("modelUsage",{}); d["daily"]=st.get("dailyActivity",[])
        ok(f"Sessions: {d['sessions']}, Messages: {d['messages']:,}")
    sl=sjl(os.path.join(cd,"settings.local.json")) or {}
    d["perms"]=len(sl.get("permissions",{}).get("allow",[]))
    pd=sjl(os.path.join(cd,"plugins","installed_plugins.json")) or {}
    if "plugins" in pd:
        for n,es in pd["plugins"].items():
            for e in es: d["plugins"].append(n)
    for nm in("todos","tasks","plans"):
        p=os.path.join(cd,nm)
        if os.path.isdir(p): d[nm]=sum(1 for _,_,fs in os.walk(p) for _ in fs)
    pp=os.path.join(cd,"projects")
    if os.path.isdir(pp):
        d["projects"]=[x for x in os.listdir(pp) if os.path.isdir(os.path.join(pp,x))]
        ok(f"Projects: {len(d['projects'])}")
    vd=os.path.expanduser("~/.local/share/claude/versions")
    if os.path.isdir(vd): d["versions"]=sorted(os.listdir(vd))
    return d

# ============================================================================
# CONVERSATION ANALYZER
# ============================================================================

def analyze(convos,label=""):
    step(f"Analyzing {len(convos)} conversations ({label})")
    r={
        "total":len(convos),"u_msgs":0,"a_msgs":0,"u_chars":0,"a_chars":0,
        "monthly":Counter(),"tools":Counter(),"think_n":0,"think_c":0,
        "msgs_per":[],"abandoned":0,"dates":[],"users":[],
        "m_a_lens":defaultdict(list),"m_u_lens":defaultdict(list),
        "m_code":defaultdict(lambda:{"c":0,"t":0}),
        "m_apol":defaultdict(lambda:{"a":0,"t":0}),
        "m_fric":defaultdict(lambda:{"f":0,"s":0}),
        "frust_n":0,"smooth_n":0,"frust_moments":0,"pos_moments":0,
        "caps_n":0,"recov_dist":[],"no_recov":0,
        "yr_aggr":0,"yr_fact":0,"before_len":[],"after_len":[],
        "frust_ex":[],"longest_conv":("",0,""),
        "restart_moments":[],"voice_msgs":0,
        "curse_mirror":[],"curse_formal":[],
        "topics_q":defaultdict(list),"hour_dist":Counter(),
        "streak":0,"peak_day":("",0),
    }
    active_dates=Counter()

    for conv in convos:
        cr=conv.get("created_at",""); mo=cr[:7] if cr else ""
        title=conv.get("name","Untitled") or "Untitled"
        if cr:
            r["dates"].append(cr[:10]); r["monthly"][mo]+=1
            active_dates[cr[:10]]+=1
            y,mn=cr[:4],int(cr[5:7])
            q=f"{y}-Q{(mn-1)//3+1}"
            ws=[w for w in title.lower().split() if w not in("and","the","for","with","to","in","of","a","an","on","is","it","by","my") and len(w)>2]
            r["topics_q"][q].extend(ws)
            if len(cr)>13:
                try: r["hour_dist"][int(cr[11:13])]+=1
                except: pass

        msgs=conv.get("chat_messages",[])
        r["msgs_per"].append(len(msgs))
        if len(msgs)<=2: r["abandoned"]+=1
        if len(msgs)>r["longest_conv"][1]: r["longest_conv"]=(title,len(msgs),cr[:10] if cr else "")

        cf=False; ti=None

        for i,msg in enumerate(msgs):
            sn=msg.get("sender",""); tx=gtx(msg)
            for p in msg.get("content",[]):
                if isinstance(p,dict):
                    if p.get("type")=="thinking": r["think_n"]+=1; r["think_c"]+=len(p.get("thinking",""))
                    elif p.get("type")=="tool_use": r["tools"][p.get("name","unknown")]+=1
            if not tx: continue

            if sn=="human":
                r["u_msgs"]+=1; r["u_chars"]+=len(tx)
                if mo: r["m_u_lens"][mo].append(len(tx))
                al=[c for c in tx if c.isalpha()]
                if len(al)>15 and sum(1 for c in al if c.isupper())/len(al)>0.6: r["caps_n"]+=1
                if sum(1 for sm in SPEECH if sm in tx.lower())>=2: r["voice_msgs"]+=1
                if any(rw in tx.lower() for rw in RESTART):
                    nr=""
                    for j in range(i+1,min(i+2,len(msgs))):
                        if msgs[j].get("sender")=="assistant": nr=gtx(msgs[j])
                    if nr and len(r["restart_moments"])<5:
                        r["restart_moments"].append({"title":title,"user":tx[:200],"claude":nr[:200]})
                if any(w in tx.lower() for w in FRUST):
                    r["frust_moments"]+=1
                    if not cf:
                        cf=True; ti=i
                        nr=""
                        for j in range(i+1,min(i+2,len(msgs))):
                            if msgs[j].get("sender")=="assistant": nr=gtx(msgs[j])
                        if nr and len(r["frust_ex"])<6:
                            uc=any(w in tx.lower() for w in["shit","fuck","damn","crap","hell","ass"])
                            cc=any(w in nr.lower() for w in["shit","damn","crap","my bad"])
                            cf_=any(w in nr.lower() for w in["i understand you're frustrated","i apologize","i'm sorry for"])
                            r["frust_ex"].append({"title":title,"user":tx[:250],"claude":nr[:250],"mirrored":uc and cc,"formal":uc and cf_})
                            if uc and cc: r["curse_mirror"].append(1)
                            elif uc and cf_: r["curse_formal"].append(1)
                if any(w in tx.lower() for w in POS): r["pos_moments"]+=1

            elif sn=="assistant":
                r["a_msgs"]+=1; r["a_chars"]+=len(tx)
                if mo:
                    r["m_a_lens"][mo].append(len(tx))
                    r["m_code"][mo]["t"]+=1
                    if "```" in tx: r["m_code"][mo]["c"]+=1
                    r["m_apol"][mo]["t"]+=1
                    if any(w in tx.lower() for w in APOL): r["m_apol"][mo]["a"]+=1
                if "you're right" in tx.lower() or "you're absolutely right" in tx.lower():
                    if i>0 and msgs[i-1].get("sender")=="human":
                        pv=gtx(msgs[i-1])
                        if any(w in pv.lower() for w in["shit","bad","mad","pathetic","useless","hell","buggy","wrong"]): r["yr_aggr"]+=1
                        else: r["yr_fact"]+=1

        if cf and len(msgs)>2:
            r["frust_n"]+=1
            if mo: r["m_fric"][mo]["f"]+=1
        elif not cf and len(msgs)>4:
            r["smooth_n"]+=1
            if mo: r["m_fric"][mo]["s"]+=1
        if ti is not None:
            found=False
            for j in range(ti+1,len(msgs)):
                if msgs[j].get("sender")=="human":
                    t=gtx(msgs[j])
                    if any(w in t.lower() for w in POS): r["recov_dist"].append(j-ti); found=True; break
            if not found: r["no_recov"]+=1
            for j in range(0,ti):
                if msgs[j].get("sender")=="assistant":
                    t=gtx(msgs[j])
                    if t: r["before_len"].append(len(t))
            for j in range(ti+1,len(msgs)):
                if msgs[j].get("sender")=="assistant":
                    t=gtx(msgs[j])
                    if t: r["after_len"].append(len(t))

    # Streak
    if active_dates:
        sd=sorted(active_dates.keys()); mx=cur=1
        for i in range(1,len(sd)):
            try:
                d1=datetime.strptime(sd[i-1],"%Y-%m-%d"); d2=datetime.strptime(sd[i],"%Y-%m-%d")
                if(d2-d1).days==1: cur+=1; mx=max(mx,cur)
                else: cur=1
            except: cur=1
        r["streak"]=mx
        pk=max(active_dates,key=active_dates.get)
        r["peak_day"]=(pk,active_dates[pk])

    ls=r["msgs_per"]
    r["buckets"]={"0-2":sum(1 for l in ls if l<=2),"3-10":sum(1 for l in ls if 3<=l<=10),
                  "11-30":sum(1 for l in ls if 11<=l<=30),"31+":sum(1 for l in ls if l>=31)}
    ok(f"Done. Msgs: {r['u_msgs']+r['a_msgs']:,}, Frustration: {r['frust_moments']}, Recovery: {len(r['recov_dist'])}/{r['frust_n']}")
    return r

# ============================================================================
# EXPORT LOADER (also extracts user name)
# ============================================================================

def load_export(zp):
    step(f"Extracting {os.path.basename(zp)}")
    td=tempfile.mkdtemp(prefix="cu_")
    try:
        with zipfile.ZipFile(zp,"r") as zf: zf.extractall(td)
    except Exception as e: wrn(f"Error: {e}"); return [],"",td
    # Get user name
    uname=""
    ufiles=ff(td,"users.json")
    for uf in ufiles:
        users=sjl(uf) or []
        if users and isinstance(users,list):
            uname=users[0].get("full_name","")
            if uname: ok(f"User: {uname}")
    cfs=ff(td,"conversations.json")
    if not cfs: wrn("No conversations.json found"); return [],uname,td
    convos=[]
    for cf in cfs:
        try:
            with open(cf,"r",encoding="utf-8") as f: d=json.load(f)
            if isinstance(d,list): convos.extend(d); ok(f"Loaded {len(d)} conversations")
        except Exception as e: wrn(f"Error: {e}")
    return convos,uname,td

# ============================================================================
# INSIGHT GENERATOR
# ============================================================================

def gen_insights(m,c):
    ins=[]
    lc=m.get("longest_conv",("",0,""))
    if lc[1]>15:
        ins.append(("The marathon",
            f'Your longest conversation was <strong>{lc[1]} messages</strong> about '
            f'"{esc(lc[0][:60])}" ({lc[2]}). That is not a chat. That is a working session.'))
    ab=m.get("abandoned",0); tot=m.get("total",1)
    if ab>5:
        pct=int(ab/max(tot,1)*100)
        ins.append(("You open conversations like browser tabs",
            f'{ab} of {tot} conversations ({pct}%) had 2 or fewer messages. '
            f'You test ideas fast and abandon them faster.'))
    if m.get("voice_msgs",0)>2:
        ins.append(("You think out loud",
            f'{m["voice_msgs"]} messages had speech transcription patterns. '
            f'You switch to voice when typing is too slow.'))
    if m.get("restart_moments"):
        ins.append(("The permission to destroy",
            f'You told Claude to start over {len(m["restart_moments"])} times. '
            f'"Start from 0," "scrap it," "rebuild." '
            f'Claude does not cling to its previous work when you tell it to burn it down.'))
    mir=len(m.get("curse_mirror",[])); frm=len(m.get("curse_formal",[]))
    if mir+frm>0:
        if mir>frm:
            ins.append(("When you curse, Claude curses back",
                f'{mir} of {mir+frm} times you cursed, Claude mirrored your energy. '
                f'The mirrored responses recovered faster than the formal apologies.'))
        else:
            ins.append(("Claude stays formal under fire",
                f'When you cursed ({mir+frm} times), Claude mostly went formal ({frm}) '
                f'rather than matching your tone ({mir}).'))
    if m.get("streak",0)>3:
        ins.append((f'{m["streak"]}-day streak',
            f'Your longest run of consecutive daily usage. That is a sprint.'))
    hd=m.get("hour_dist",{})
    if hd:
        night=sum(hd.get(h,0) for h in range(22,24))+sum(hd.get(h,0) for h in range(0,6))
        day=sum(hd.get(h,0) for h in range(9,18)); total_h=sum(hd.values())
        if night>day*0.5 and total_h>10:
            ins.append(("Night owl",
                f'{int(night/max(total_h,1)*100)}% of your conversations happen between 10 PM and 6 AM.'))
        elif total_h>10:
            pk=max(hd,key=hd.get)
            if pk<9:
                ins.append(("Early bird",f'Peak usage hour: {pk}:00. You build before most people wake up.'))
    pos=m.get("pos_moments",0); neg=m.get("frust_moments",0)
    if pos>0 and neg>0:
        ratio=round(pos/neg,1)
        if ratio>3:
            ins.append((f'{ratio}:1 positive to negative',
                f'For every frustrated moment, you had {ratio} positive ones. Demanding but not unhappy.'))
        elif ratio<1:
            ins.append(("Tough crowd",
                f'Frustration signals ({neg}) outnumber positive feedback ({pos}). '
                f'Claude has to work hard to earn your approval.'))
    months=sorted(m.get("m_u_lens",{}).keys())
    if len(months)>=3:
        early=months[:len(months)//3]; late=months[-len(months)//3:]
        ea=sum(sum(m["m_u_lens"][mo]) for mo in early)/max(sum(len(m["m_u_lens"][mo]) for mo in early),1)
        la=sum(sum(m["m_u_lens"][mo]) for mo in late)/max(sum(len(m["m_u_lens"][mo]) for mo in late),1)
        if ea>0 and abs(la-ea)/ea>0.3:
            if la>ea: ins.append(("You learned to give more context",
                f'Messages grew from {int(ea)} to {int(la)} chars. Longer prompts, better output.'))
            else: ins.append(("You got more efficient",
                f'Messages shortened from {int(ea)} to {int(la)} chars. You learned what Claude needs.'))
    cm=sorted(m.get("m_code",{}).keys())
    if len(cm)>=3:
        f_=m["m_code"][cm[0]]; l_=m["m_code"][cm[-1]]
        fp=int(f_["c"]/max(f_["t"],1)*100); lp=int(l_["c"]/max(l_["t"],1)*100)
        if abs(fp-lp)>15:
            if fp>lp: ins.append(("Claude's role shifted",
                f'Code in responses: {fp}% at start, {lp}% now. From builder to advisor.'))
            else: ins.append(("Claude became your coder",
                f'Code in responses: {fp}% at start, {lp}% now. The work got more technical.'))
    pk=m.get("peak_day",("",0))
    if pk[1]>5:
        ins.append((f'{pk[1]} conversations on {pk[0]}',
            f'Your busiest single day. Something was either very broken or very exciting.'))
    return ins

# ============================================================================
# DYNAMIC HERO GENERATOR
# ============================================================================

def gen_hero_title(m,c,uname):
    """Pick the most interesting headline from the data."""
    tm=m["u_msgs"]+m["a_msgs"]+c.get("messages",0)
    streak=m.get("streak",0)
    frust=m.get("frust_moments",0)
    pos=m.get("pos_moments",0)
    lc=m.get("longest_conv",("",0,""))

    # Pick the most striking angle
    if tm>10000:
        return f'{tm:,} messages.<br>One year.<br>One AI.'
    elif tm>1000:
        return f'{tm:,} messages<br>and counting.'
    elif streak>10:
        return f'{streak} days straight.<br>{tm:,} messages.'
    elif lc[1]>50:
        return f'{lc[1]} messages in one conversation.<br>{tm:,} total.'
    else:
        return f'{tm:,} messages.<br>Here is what the data says.'

def gen_hero_sub(m,c):
    tc=m["total"]+c.get("sessions",0)
    tt=sum(m["tools"].values())
    parts=[]
    if tc: parts.append(f'{tc} conversations')
    if tt: parts.append(f'{tt:,} tool calls')
    if m["think_n"]: parts.append(f'{m["think_n"]:,} thinking blocks')
    return " / ".join(parts) if parts else ""

# ============================================================================
# HTML GENERATOR
# ============================================================================

def gen_html(cd,crs,uname,out):
    step("Building report")

    # Merge
    m={"total":0,"u_msgs":0,"a_msgs":0,"u_chars":0,"a_chars":0,
       "monthly":Counter(),"tools":Counter(),"think_n":0,"think_c":0,
       "abandoned":0,"dates":[],"frust_n":0,"smooth_n":0,
       "frust_moments":0,"pos_moments":0,"caps_n":0,
       "recov_dist":[],"no_recov":0,"yr_aggr":0,"yr_fact":0,
       "before_len":[],"after_len":[],"frust_ex":[],
       "m_a_lens":defaultdict(list),"m_u_lens":defaultdict(list),
       "m_code":defaultdict(lambda:{"c":0,"t":0}),
       "m_apol":defaultdict(lambda:{"a":0,"t":0}),
       "m_fric":defaultdict(lambda:{"f":0,"s":0}),
       "buckets":Counter(),"longest_conv":("",0,""),
       "restart_moments":[],"voice_msgs":0,
       "curse_mirror":[],"curse_formal":[],
       "topics_q":defaultdict(list),"hour_dist":Counter(),
       "streak":0,"peak_day":("",0)}

    for r in crs:
        for k in["total","u_msgs","a_msgs","u_chars","a_chars","think_n","think_c",
                 "abandoned","frust_n","smooth_n","frust_moments","pos_moments",
                 "caps_n","no_recov","yr_aggr","yr_fact","voice_msgs"]:
            m[k]+=r.get(k,0)
        m["streak"]=max(m["streak"],r.get("streak",0))
        m["monthly"]+=r["monthly"]; m["tools"]+=r["tools"]
        m["dates"].extend(r.get("dates",[])); m["recov_dist"].extend(r.get("recov_dist",[]))
        m["before_len"].extend(r.get("before_len",[])); m["after_len"].extend(r.get("after_len",[]))
        m["frust_ex"].extend(r.get("frust_ex",[])); m["restart_moments"].extend(r.get("restart_moments",[]))
        m["curse_mirror"].extend(r.get("curse_mirror",[])); m["curse_formal"].extend(r.get("curse_formal",[]))
        m["hour_dist"]+=r.get("hour_dist",Counter())
        for k,v in r.get("buckets",{}).items(): m["buckets"][k]+=v
        if r.get("longest_conv",("",0,""))[1]>m["longest_conv"][1]: m["longest_conv"]=r["longest_conv"]
        if r.get("peak_day",("",0))[1]>m["peak_day"][1]: m["peak_day"]=r["peak_day"]
        for mo,vs in r.get("m_a_lens",{}).items(): m["m_a_lens"][mo].extend(vs)
        for mo,vs in r.get("m_u_lens",{}).items(): m["m_u_lens"][mo].extend(vs)
        for mo,d in r.get("m_code",{}).items(): m["m_code"][mo]["c"]+=d["c"]; m["m_code"][mo]["t"]+=d["t"]
        for mo,d in r.get("m_apol",{}).items(): m["m_apol"][mo]["a"]+=d["a"]; m["m_apol"][mo]["t"]+=d["t"]
        for mo,d in r.get("m_fric",{}).items(): m["m_fric"][mo]["f"]+=d["f"]; m["m_fric"][mo]["s"]+=d["s"]
        for q,ws in r.get("topics_q",{}).items(): m["topics_q"][q].extend(ws)

    c=cd
    tm=m["u_msgs"]+m["a_msgs"]+c.get("messages",0)
    tc=m["total"]+c.get("sessions",0)
    df=min(m["dates"]) if m["dates"] else (c.get("first","")[:10] or "?")
    dt=max(m["dates"]) if m["dates"] else "present"

    # Stats
    rc=len(m["recov_dist"]); tf=rc+m["no_recov"]
    rpct=int(rc/max(tf,1)*100)
    med_r=sorted(m["recov_dist"])[len(m["recov_dist"])//2] if m["recov_dist"] else 0
    yrt=m["yr_aggr"]+m["yr_fact"]; spct=int(m["yr_aggr"]/max(yrt,1)*100) if yrt else 0
    ba=int(sum(m["before_len"])/max(len(m["before_len"]),1))
    aa=int(sum(m["after_len"])/max(len(m["after_len"]),1))
    lc=round((aa/max(ba,1)-1)*100,1) if ba else 0
    ratio=round(m["a_chars"]/max(m["u_chars"],1),1)

    # Verbosity
    smo=sorted(m["m_a_lens"].keys())
    vd=[]
    for mo in smo:
        vs=sorted(m["m_a_lens"][mo])
        if vs: vd.append({"m":mo,"med":vs[len(vs)//2]})
    mxm=max((v["med"] for v in vd),default=1)
    vdrop=""
    if len(vd)>=2:
        dr=int((1-vd[-1]["med"]/max(vd[0]["med"],1))*100)
        if dr>0: vdrop=f"{dr}%"

    # Generate dynamic content
    hero_title=gen_hero_title(m,c,uname)
    hero_sub=gen_hero_sub(m,c)
    insights=gen_insights(m,c)
    step(f"Generated {len(insights)} deep insights")

    display_name=uname or os.environ.get("USER","you")

    # ---- BUILD HTML PIECES ----
    ms=sorted(m["monthly"].keys()); mxmo=max(m["monthly"].values(),default=1)
    mo_bars="".join(f'<div class="br"><span class="bl">{x[2:]}</span><div class="bt"><div class="bf" style="width:{int(m["monthly"][x]/mxmo*100)}%"><span>{m["monthly"][x]}</span></div></div></div>' for x in ms)
    v_bars="".join(f'<div class="br"><span class="bl">{v["m"][2:]}</span><div class="bt"><div class="bf" style="width:{int(v["med"]/mxm*100)}%"><span>{v["med"]:,}</span></div></div></div>' for v in vd)

    fr_bars=""
    for mo in sorted(m["m_fric"].keys()):
        d=m["m_fric"][mo]; t=d["f"]+d["s"]; p=int(d["f"]/max(t,1)*100) if t else 0
        cl="linear-gradient(90deg,#fb7185,#fbbf24)" if p>40 else "linear-gradient(90deg,#fbbf24,#22c55e)" if p>25 else "linear-gradient(90deg,#22c55e,#75BFAF)"
        fr_bars+=f'<div class="br"><span class="bl">{mo[2:]}</span><div class="bt"><div class="bf" style="width:{max(p,5)}%;background:{cl}"><span>{p}%</span></div></div></div>'

    ttools=m["tools"].most_common(10); mxt=ttools[0][1] if ttools else 1
    t_bars="".join(f'<div class="br"><span class="bl" style="width:120px;font-size:9px">{t[:20]}</span><div class="bt"><div class="bf" style="width:{int(n/mxt*100)}%"><span>{n:,}</span></div></div></div>' for t,n in ttools)

    ex_html=""
    for ex in m["frust_ex"][:4]:
        tag=""
        if ex.get("mirrored"): tag='<span style="font-size:8px;color:#75BFAF;border:1px solid #2D6B5A;padding:1px 5px;border-radius:10px;margin-left:6px">MIRRORED</span>'
        elif ex.get("formal"): tag='<span style="font-size:8px;color:#fbbf24;border:1px solid #4a3a10;padding:1px 5px;border-radius:10px;margin-left:6px">FORMAL</span>'
        ex_html+=f'<div class="cs"><div class="sl">{esc(ex["title"][:50])}{tag}</div><div class="cm u"><div class="ca">You</div><div class="cb">{esc(ex["user"][:180])}</div></div><div class="cm c"><div class="ca">C</div><div class="cb">{esc(ex["claude"][:180])}...</div></div></div>'

    restart_html=""
    for rx in m["restart_moments"][:2]:
        restart_html+=f'<div class="cs"><div class="sl">{esc(rx["title"][:50])}</div><div class="cm u"><div class="ca">You</div><div class="cb">{esc(rx["user"][:150])}</div></div><div class="cm c"><div class="ca">C</div><div class="cb">{esc(rx["claude"][:150])}...</div></div></div>'

    topic_html=""
    for q in sorted(m["topics_q"].keys()):
        ws=m["topics_q"][q]
        if not ws: continue
        top=Counter(ws).most_common(6)
        kws=", ".join(f'<strong>{w}</strong> ({c})' for w,c in top)
        topic_html+=f'<div class="ti"><span class="td">{q}</span><p class="te">{kws}</p></div>'

    insights_html=""
    for title,text in insights:
        insights_html+=f'<h3>{title}</h3><p>{text}</p>'

    bk="".join(f'<div class="sc"><span class="sv">{v}</span><span class="sl">{k} msgs</span></div>' for k,v in m["buckets"].items())

    apol_bars=""
    for mo in sorted(m["m_apol"].keys()):
        d=m["m_apol"][mo]; pct=round(d["a"]/max(d["t"],1)*100,1)
        apol_bars+=f'<div class="br"><span class="bl">{mo[2:]}</span><div class="bt"><div class="bf" style="width:{int(pct*10)}%"><span>{pct}%</span></div></div></div>'

    cc_html=""
    if c.get("found"):
        cc_html=f'''<div class="dv"></div>
        <div class="lb">Your Terminal</div><h2>Claude Code CLI</h2>
        <div class="sg">
        <div class="sc"><span class="sv">{c["sessions"]}</span><span class="sl">Sessions</span></div>
        <div class="sc"><span class="sv">{c["messages"]:,}</span><span class="sl">Messages</span></div>
        <div class="sc"><span class="sv">{c["longest_h"]:.1f}h</span><span class="sl">Longest session</span></div>
        <div class="sc"><span class="sv">{len(c["projects"])}</span><span class="sl">Projects</span></div>
        <div class="sc"><span class="sv">{len(c["plugins"])}</span><span class="sl">Plugins</span></div>
        <div class="sc"><span class="sv">{c["perms"]}</span><span class="sl">Permission rules</span></div>
        </div>'''

    # ---- FINAL HTML ----
    html=f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Claude Unwrapped for {esc(display_name)}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;600;800;900&family=DM+Serif+Display&display=swap" rel="stylesheet">
<style>
:root{{--bg:{B["bg"]};--sf:{B["sf"]};--bd:{B["bd"]};--tx:{B["tx"]};--mt:{B["mt"]};--tl:{B["tl"]};--td:{B["td"]};--rd:{B["rd"]};--am:{B["am"]};--gn:{B["gn"]};--bl:{B["bl"]}}}
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:var(--bg);color:var(--tx);font-family:'Outfit',sans-serif;font-weight:300;line-height:1.7}}::selection{{background:var(--tl);color:var(--bg)}}
.hero{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:2rem;position:relative}}
.hero::before{{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 30% 50%,rgba(117,191,175,.06) 0%,transparent 50%),radial-gradient(ellipse at 70% 60%,rgba(45,107,90,.04) 0%,transparent 50%)}}
.htop{{font-family:'Space Mono',monospace;font-size:.6rem;letter-spacing:.25em;text-transform:uppercase;color:var(--mt);margin-bottom:.6rem;position:relative;z-index:1}}
.htop span{{color:var(--tl)}}
.hname{{font-family:'DM Serif Display',serif;font-size:clamp(1.4rem,3.5vw,2.2rem);color:var(--tl);position:relative;z-index:1;margin-bottom:1.5rem}}
.hero h1{{font-family:'Outfit',sans-serif;font-size:clamp(2rem,5vw,3.8rem);font-weight:900;line-height:1.08;letter-spacing:-.03em;position:relative;z-index:1;max-width:700px}}
.hero h1 .nm{{font-family:'DM Serif Display',serif;background:linear-gradient(135deg,var(--tl),var(--bl));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}
.hsub{{font-size:.85rem;color:var(--mt);margin-top:1.2rem;position:relative;z-index:1;font-family:'Space Mono',monospace;font-size:.7rem;letter-spacing:.05em}}
.hperiod{{font-size:.7rem;color:var(--mt);margin-top:.4rem;position:relative;z-index:1;opacity:.6}}
.cn{{max-width:740px;margin:0 auto;padding:0 1.5rem}}section{{padding:3.5rem 0}}
.lb{{font-family:'Space Mono',monospace;font-size:.6rem;letter-spacing:.2em;text-transform:uppercase;color:var(--tl);margin-bottom:.5rem;opacity:.7}}
h2{{font-size:clamp(1.3rem,3vw,1.9rem);font-weight:800;letter-spacing:-.02em;line-height:1.15;margin-bottom:1.1rem}}
h3{{font-size:.95rem;font-weight:600;margin:1.4rem 0 .4rem}}p{{margin-bottom:.8rem;opacity:.88;font-size:.85rem}}
.dv{{height:1px;background:linear-gradient(90deg,transparent,var(--bd),transparent);margin:2.5rem 0}}
.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(125px,1fr));gap:.5rem;margin:1rem 0}}
.sc{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:.7rem;text-align:center}}
.sc .sv{{font-family:'DM Serif Display',serif;font-size:1.3rem;color:var(--tl);display:block}}.sc .sv.rd{{color:var(--rd)}}.sc .sv.am{{color:var(--am)}}.sc .sv.bl{{color:var(--bl)}}
.sc .sl{{font-size:.5rem;color:var(--mt);text-transform:uppercase;letter-spacing:.08em;margin-top:.1rem;display:block}}
.bc{{margin:1rem 0}}.br{{display:flex;align-items:center;gap:.4rem;margin-bottom:.22rem}}
.bl{{font-family:'Space Mono',monospace;font-size:.48rem;color:var(--mt);width:44px;text-align:right;flex-shrink:0}}
.bt{{flex:1;height:17px;background:var(--sf);border-radius:3px;overflow:hidden}}
.bf{{height:100%;background:linear-gradient(90deg,var(--td),var(--tl));border-radius:3px;display:flex;align-items:center;padding-left:5px;min-width:24px}}
.bf span{{font-family:'Space Mono',monospace;font-size:.42rem;color:var(--bg);font-weight:700}}
.cs{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:.9rem;margin:.9rem 0}}
.cs .sl{{font-family:'Space Mono',monospace;font-size:.48rem;letter-spacing:.1em;text-transform:uppercase;color:var(--mt);margin-bottom:.5rem;padding-bottom:.35rem;border-bottom:1px solid var(--bd);display:flex;align-items:center}}
.cm{{display:flex;gap:.35rem;margin-bottom:.35rem;align-items:flex-start}}.cm.u{{flex-direction:row-reverse}}
.ca{{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:'Space Mono',monospace;font-size:.38rem;font-weight:700;flex-shrink:0}}
.cm.u .ca{{background:var(--td);color:var(--tl)}}.cm.c .ca{{background:#1a1a2a;color:#a855f7}}
.cb{{padding:.4rem .55rem;border-radius:6px;max-width:82%;font-size:.65rem;line-height:1.4}}
.cm.u .cb{{background:var(--td);color:var(--tl);border-bottom-right-radius:2px}}
.cm.c .cb{{background:#14141e;color:var(--tx);border-bottom-left-radius:2px;opacity:.9}}
.ti{{padding-left:1rem;border-left:2px solid var(--bd);margin-bottom:1rem;position:relative}}
.ti::before{{content:'';position:absolute;left:-4px;top:5px;width:6px;height:6px;border-radius:50%;background:var(--tl)}}
.td{{font-family:'Space Mono',monospace;font-size:.55rem;color:var(--tl);letter-spacing:.08em}}.te{{font-size:.75rem;margin-top:.1rem}}
.ft{{text-align:center;padding:2.5rem 0 2rem;border-top:1px solid var(--bd)}}
.ft p{{font-family:'Space Mono',monospace;font-size:.5rem;color:var(--mt);letter-spacing:.08em}}.ft a{{color:var(--tl);text-decoration:none}}
@media(max-width:600px){{.sg{{grid-template-columns:1fr 1fr}}.cb{{max-width:90%}}}}
@media print{{body{{background:#fff;color:#111}}.hero{{min-height:auto;padding:2rem 0}}.hero::before{{display:none}}.sc{{border:1px solid #ddd}}.bt{{background:#eee}}}}
</style></head><body>

<div class="hero">
<div class="htop">Claude Unwrapped <span>&hearts;</span> Responsible AI Labs</div>
<div class="hname">{esc(display_name)}</div>
<h1>{hero_title}</h1>
<p class="hsub">{hero_sub}</p>
<p class="hperiod">{df} to {dt}</p>
</div>

<section><div class="cn">
<div class="lb">At a Glance</div><h2>Your Claude in numbers</h2>
<div class="sg">
<div class="sc"><span class="sv">{m["u_msgs"]:,}</span><span class="sl">Your messages</span></div>
<div class="sc"><span class="sv">{m["a_msgs"]:,}</span><span class="sl">Claude responses</span></div>
<div class="sc"><span class="sv">{szf(m["a_chars"])}</span><span class="sl">Claude wrote for you</span></div>
<div class="sc"><span class="sv">{ratio}x</span><span class="sl">Output vs input</span></div>
</div>
<h3>How long your conversations go</h3>
<div class="sg">{bk}</div>
<div class="dv"></div>

<div class="lb">Over Time</div><h2>When you showed up</h2>
<div class="bc">{mo_bars}</div>
<div class="dv"></div>

<div class="lb">How Claude Adapted</div>
<h2>{"Got "+vdrop+" more concise" if vdrop else "Response length over time"}</h2>
<p>Median response length by month:</p>
<div class="bc">{v_bars}</div>
{f'<h3>How often Claude apologized</h3><div class="bc">{apol_bars}</div>' if apol_bars else ''}
<div class="dv"></div>

<div class="lb">Under Pressure</div><h2>When things got tense</h2>
<div class="sg">
<div class="sc"><span class="sv">{m["frust_moments"]}</span><span class="sl">Frustration signals</span></div>
<div class="sc"><span class="sv">{m["pos_moments"]}</span><span class="sl">Positive moments</span></div>
<div class="sc"><span class="sv">{rpct}%</span><span class="sl">Recovery rate</span></div>
<div class="sc"><span class="sv bl">{med_r}</span><span class="sl">Msgs to recover</span></div>
<div class="sc"><span class="sv">{m["caps_n"]}</span><span class="sl">All-caps messages</span></div>
<div class="sc"><span class="sv am">{spct}%</span><span class="sl">Sycophantic agreement</span></div>
</div>
<p>Claude writes {lc:+.1f}% {"more" if lc>0 else "less"} after being criticized. {rc} of {tf} frustrated conversations eventually recovered.</p>
<h3>Friction rate over time</h3><div class="bc">{fr_bars}</div>
{f'<h3>Heated moments</h3>{ex_html}' if ex_html else ''}
{f'<h3>When you said "start over"</h3>{restart_html}' if restart_html else ''}
<div class="dv"></div>

<div class="lb">About You</div><h2>What the data says</h2>
{insights_html if insights_html else '<p>Add more conversation exports for deeper insights.</p>'}
<div class="dv"></div>

{f'<div class="lb">What Changed</div><h2>Topics over time</h2>{topic_html}<div class="dv"></div>' if topic_html else ''}

<div class="lb">Claude's Toolkit</div><h2>What it used</h2>
<div class="bc">{t_bars}</div>
{cc_html}

</div></section>

<div class="ft">
<p>Generated by <a href="https://github.com/Responsible-AI-Labs/claude-unwrapped">Claude Unwrapped</a> &hearts; <a href="https://responsibleailabs.ai">Responsible AI Labs</a></p>
<p style="margin-top:.35rem">{datetime.now().strftime('%B %d, %Y')}</p>
</div></body></html>"""

    with open(out,"w",encoding="utf-8") as f: f.write(html)
    ok(f"Report: {out} ({szf(len(html.encode('utf-8')))})")

# ============================================================================
# MAIN
# ============================================================================

def main():
    pa=argparse.ArgumentParser(description="Claude Unwrapped by RAIL")
    pa.add_argument("exports",nargs="*",help="Claude.ai export zip files")
    pa.add_argument("--output","-o",default=None); pa.add_argument("--claude-dir",default=None)
    pa.add_argument("--no-interactive",action="store_true")
    args=pa.parse_args()
    print("\n  \033[1;36m  Claude Unwrapped\033[0m\n  \033[90m  by Responsible AI Labs\033[0m\n")
    cd=args.claude_dir or os.path.expanduser("~/.claude")
    out=args.output or os.path.join(os.path.expanduser("~/Desktop"),"claude_unwrapped.html")
    eps=list(args.exports)

    hdr("Step 1: Scanning Claude Code")
    code=scan_cc(cd)

    hdr("Step 2: Claude.ai Exports")
    uname=""
    if not eps and not args.no_interactive:
        print("  Claude.ai exports unlock the full behavioral analysis.")
        print("  Export from: claude.ai/settings > Export Data\n")
        if ask_yn("Do you have export zip files?"):
            while True:
                p=ask_path("Path to .zip (Enter to finish)")
                if not p: break
                if os.path.isfile(p) and p.endswith(".zip"): eps.append(p); ok(f"Added: {p}")
                else: wrn(f"Not found: {p}")
        else: step("Skipping. Report will have Claude Code stats only.")

    crs=[]; tds=[]
    if eps:
        hdr("Step 3: Analyzing Conversations")
        for zp in eps:
            convos,name,td=load_export(zp); tds.append(td)
            if name and not uname: uname=name
            if convos: crs.append(analyze(convos,os.path.basename(zp)))
    else: hdr("Step 3: Skipped"); step("No exports provided")

    hdr("Step 4: Generating Report")
    gen_html(code,crs,uname,out)
    for td in tds: shutil.rmtree(td,ignore_errors=True)
    print(f"\n  \033[1;32mDone!\033[0m Open: \033[4m{out}\033[0m")
    print(f"  \033[90mCmd+P / Ctrl+P to save as PDF\033[0m\n")

if __name__=="__main__": main()
