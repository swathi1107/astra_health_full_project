from datetime import datetime, date, timedelta
from statistics import mean, pstdev
from pathlib import Path
import csv, io, os
from fastapi import FastAPI, Depends, HTTPException, Response, Request, Cookie
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from .database import Base, engine, get_db
from . import models as m
from .schemas import LoginIn, UserCreate, AstronautIn, MissionIn, ReadingIn, ReviewIn, AlertAction
from .security import hash_password, verify_password, make_session, read_session

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ASTRA HEALTH API", version="1.0.0", description="Offline-first astronaut health research and decision-support prototype")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")
ROLES = {"administrator", "astronaut", "medical_officer", "researcher"}

def audit(db, user, action, entity, entity_id=None, details=""):
    db.add(m.AuditLog(user_id=user.id if user else None, action=action, entity=entity, entity_id=entity_id, details=details))

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("astra_session")
    uid = read_session(token) if token else None
    user = db.get(m.User, uid) if uid else None
    if not user or not user.active:
        raise HTTPException(401, "Please log in")
    return user

def require(*roles):
    def dep(user=m.Depends if False else None):
        pass
    def checker(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission for this action")
        return user
    return checker

def seed_admin(db):
    if not db.query(m.User).filter(m.User.username == "admin").first():
        db.add(m.User(username="admin", email="admin@astra.local", password_hash=hash_password("AdminDemo123!"), role="administrator"))
        db.commit()

@app.on_event("startup")
def startup():
    with next(get_db()) as db:
        seed_admin(db)

@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(func.count().select())
        return {"status": "ok", "database": "connected", "mode": "local"}
    except Exception as e:
        raise HTTPException(503, "Database unavailable")

@app.post("/api/auth/register")
def register(data: UserCreate, db: Session = Depends(get_db)):
    if data.role not in {"astronaut", "researcher"}:
        raise HTTPException(403, "Self-registration is limited to astronaut and researcher roles")
    if db.query(m.User).filter((m.User.username == data.username) | (m.User.email == data.email)).first():
        raise HTTPException(409, "Username or email already exists")
    user = m.User(username=data.username, email=data.email, password_hash=hash_password(data.password), role=data.role)
    db.add(user); db.commit(); db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role}

@app.post("/api/auth/login")
def login(data: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(m.User).filter(m.User.username == data.username).first()
    if not user or not user.active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    response.set_cookie("astra_session", make_session(user.id), httponly=True, samesite="lax",
                        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", max_age=43200)
    audit(db, user, "LOGIN", "user", user.id); db.commit()
    return {"id": user.id, "username": user.username, "role": user.role}

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("astra_session")
    return {"message": "Logged out"}

@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "role": user.role}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(current_user)):
    return {
        "astronauts": db.query(m.Astronaut).count(),
        "active_missions": db.query(m.Mission).filter(m.Mission.status == "Active").count(),
        "readings": db.query(m.Reading).count(),
        "pending_reviews": db.query(m.Baseline).filter(m.Baseline.status == "Pending").count(),
        "active_alerts": db.query(m.Alert).filter(m.Alert.status != "Resolved").count(),
        "approved_baselines": db.query(m.Baseline).filter(m.Baseline.status == "Approved").count(),
        "recent_readings": [reading_dict(x) for x in db.query(m.Reading).order_by(m.Reading.recorded_at.desc()).limit(8)],
        "recent_alerts": [alert_dict(x) for x in db.query(m.Alert).order_by(m.Alert.created_at.desc()).limit(5)]
    }

def reading_dict(x):
    return {"id":x.id,"astronaut_id":x.astronaut_id,"mission_id":x.mission_id,"heart_rate":x.heart_rate,"spo2":x.spo2,
            "systolic_bp":x.systolic_bp,"diastolic_bp":x.diastolic_bp,"activity":x.activity,"mission_phase":x.mission_phase,
            "sensor_source":x.sensor_source,"quality_status":x.quality_status,"environment":x.environment,
            "recorded_at":x.recorded_at.isoformat() if x.recorded_at else None}

def alert_dict(x):
    return {"id":x.id,"astronaut_id":x.astronaut_id,"parameter":x.parameter,"observed":x.observed,
            "baseline_value":x.baseline_value,"deviation":x.deviation,"severity":x.severity,"reason":x.reason,
            "status":x.status,"created_at":x.created_at.isoformat()}

@app.get("/api/astronauts")
def list_astronauts(q: str = "", db: Session = Depends(get_db), user=Depends(current_user)):
    query = db.query(m.Astronaut)
    if user.role == "astronaut":
        query = query.filter(m.Astronaut.email == user.email)
    if q: query = query.filter(m.Astronaut.full_name.ilike(f"%{q}%") | m.Astronaut.astronaut_code.ilike(f"%{q}%"))
    return [{"id":x.id,"astronaut_code":x.astronaut_code,"full_name":x.full_name,"email":x.email,"status":x.status,"notes":x.notes} for x in query.order_by(m.Astronaut.full_name).all()]

@app.post("/api/astronauts")
def create_astronaut(data: AstronautIn, db: Session = Depends(get_db), user=Depends(require("administrator","medical_officer"))):
    if db.query(m.Astronaut).filter_by(astronaut_code=data.astronaut_code).first(): raise HTTPException(409,"Astronaut ID already exists")
    x=m.Astronaut(**data.model_dump()); db.add(x); db.flush(); audit(db,user,"CREATE","astronaut",x.id); db.commit(); db.refresh(x)
    return {"id":x.id,"astronaut_code":x.astronaut_code,"full_name":x.full_name,"email":x.email,"status":x.status,"notes":x.notes}

@app.put("/api/astronauts/{aid}")
def update_astronaut(aid:int,data:AstronautIn,db:Session=Depends(get_db),user=Depends(require("administrator","medical_officer"))):
    x=db.get(m.Astronaut,aid)
    if not x: raise HTTPException(404,"Astronaut not found")
    for k,v in data.model_dump().items(): setattr(x,k,v)
    audit(db,user,"UPDATE","astronaut",aid); db.commit()
    return {"message":"Astronaut updated"}

@app.delete("/api/astronauts/{aid}")
def deactivate_astronaut(aid:int,db:Session=Depends(get_db),user=Depends(require("administrator"))):
    x=db.get(m.Astronaut,aid)
    if not x: raise HTTPException(404,"Astronaut not found")
    x.status="Inactive"; audit(db,user,"DEACTIVATE","astronaut",aid); db.commit()
    return {"message":"Astronaut deactivated; historical records retained"}

@app.get("/api/missions")
def list_missions(db:Session=Depends(get_db),user=Depends(current_user)):
    return [{"id":x.id,"name":x.name,"description":x.description,"status":x.status,"phase":x.phase,
             "start_date":x.start_date.isoformat() if x.start_date else None,"end_date":x.end_date.isoformat() if x.end_date else None} for x in db.query(m.Mission).order_by(m.Mission.id.desc()).all()]

@app.post("/api/missions")
def create_mission(data:MissionIn,db:Session=Depends(get_db),user=Depends(require("administrator","medical_officer"))):
    if data.start_date and data.end_date and data.end_date < data.start_date: raise HTTPException(422,"End date cannot be before start date")
    if db.query(m.Mission).filter_by(name=data.name).first(): raise HTTPException(409,"Mission name already exists")
    x=m.Mission(**data.model_dump()); db.add(x); db.flush(); audit(db,user,"CREATE","mission",x.id); db.commit(); db.refresh(x)
    return {"id":x.id,"name":x.name,"status":x.status,"phase":x.phase}

@app.post("/api/missions/{mid}/assign/{aid}")
def assign_mission(mid:int,aid:int,db:Session=Depends(get_db),user=Depends(require("administrator","medical_officer"))):
    if not db.get(m.Mission,mid) or not db.get(m.Astronaut,aid): raise HTTPException(404,"Mission or astronaut not found")
    if not db.query(m.MissionAssignment).filter_by(mission_id=mid,astronaut_id=aid).first():
        db.add(m.MissionAssignment(mission_id=mid,astronaut_id=aid)); audit(db,user,"ASSIGN","mission",mid,f"astronaut_id={aid}"); db.commit()
    return {"message":"Assignment saved"}

def evaluate_reading(db, user, x):
    baseline=db.query(m.Baseline).filter_by(astronaut_id=x.astronaut_id,status="Approved").order_by(m.Baseline.version.desc()).first()
    if not baseline or x.quality_status != "VALID": return
    checks=[("heart_rate",x.heart_rate,baseline.avg_heart_rate,baseline.std_heart_rate),
            ("spo2",x.spo2,baseline.avg_spo2,0),("systolic_bp",x.systolic_bp,baseline.avg_systolic,0),
            ("diastolic_bp",x.diastolic_bp,baseline.avg_diastolic,0)]
    for name,val,ref,std in checks:
        delta=val-ref
        # Research-only configurable rule: >2 SD where SD exists, otherwise >10% relative deviation.
        threshold=max(2*std, abs(ref)*0.10) if std and std>0 else abs(ref)*0.10
        if abs(delta)>threshold:
            severity="High" if abs(delta)>max(threshold*2,abs(ref)*0.20) else "Moderate"
            db.add(m.Alert(astronaut_id=x.astronaut_id,reading_id=x.id,parameter=name,observed=val,
                           baseline_value=ref,deviation=delta,severity=severity,
                           reason=f"{name} differs from approved personal baseline by {delta:.2f}; research rule threshold {threshold:.2f}. Not a diagnosis."))
            db.add(m.Notification(title="New statistical deviation",message=f"A {severity.lower()} {name} deviation was generated for astronaut #{x.astronaut_id}."))
    audit(db,user,"EVALUATE","reading",x.id,"Statistical comparison against approved baseline")

@app.post("/api/readings")
def create_reading(data:ReadingIn,db:Session=Depends(get_db),user=Depends(current_user)):
    if user.role=="astronaut":
        astronaut=db.query(m.Astronaut).filter_by(email=user.email).first()
        if not astronaut or astronaut.id != data.astronaut_id: raise HTTPException(403,"You can only submit your own readings")
    if not db.get(m.Astronaut,data.astronaut_id): raise HTTPException(404,"Astronaut not found")
    if data.mission_id and not db.get(m.Mission,data.mission_id): raise HTTPException(404,"Mission not found")
    if data.sync_key:
        old=db.query(m.Reading).filter_by(sync_key=data.sync_key).first()
        if old: return {"id":old.id,"duplicate":True,"message":"Already synchronised"}
    if data.quality_status not in {"VALID","INVALID","SUSPECT"}: raise HTTPException(422,"Invalid quality status")
    payload=data.model_dump(); payload["recorded_at"]=payload["recorded_at"] or datetime.utcnow()
    x=m.Reading(**payload); db.add(x); db.flush(); evaluate_reading(db,user,x); audit(db,user,"CREATE","reading",x.id); db.commit()
    return {"id":x.id,"message":"Reading saved to server","duplicate":False}

@app.get("/api/readings")
def list_readings(astronaut_id:int|None=None,environment:str|None=None,limit:int=100,db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Reading)
    if user.role=="astronaut":
        a=db.query(m.Astronaut).filter_by(email=user.email).first()
        if not a: return []
        q=q.filter(m.Reading.astronaut_id==a.id)
    if astronaut_id: q=q.filter(m.Reading.astronaut_id==astronaut_id)
    if environment: q=q.filter(m.Reading.environment==environment.upper())
    return [reading_dict(x) for x in q.order_by(m.Reading.recorded_at.desc()).limit(min(limit,500)).all()]

@app.post("/api/baselines/{aid}/calculate")
def calculate_baseline(aid:int,db:Session=Depends(get_db),user=Depends(require("administrator","medical_officer"))):
    if not db.get(m.Astronaut,aid): raise HTTPException(404,"Astronaut not found")
    rows=db.query(m.Reading).filter_by(astronaut_id=aid,environment="EARTH",activity="RESTING",quality_status="VALID").all()
    if len(rows)<5: raise HTTPException(422,f"Five valid Earth RESTING readings required; currently {len(rows)}")
    # Use latest five eligible records, preserving repeatable cohort definition.
    rows=sorted(rows,key=lambda r:r.recorded_at)[-5:]
    hrs=[r.heart_rate for r in rows]; spo=[r.spo2 for r in rows]; sys=[r.systolic_bp for r in rows]; dia=[r.diastolic_bp for r in rows]
    version=(db.query(func.max(m.Baseline.version)).filter_by(astronaut_id=aid).scalar() or 0)+1
    b=m.Baseline(astronaut_id=aid,version=version,status="Pending",reading_count=5,
       avg_heart_rate=mean(hrs),min_heart_rate=min(hrs),max_heart_rate=max(hrs),std_heart_rate=pstdev(hrs),
       avg_spo2=mean(spo),min_spo2=min(spo),max_spo2=max(spo),avg_systolic=mean(sys),avg_diastolic=mean(dia))
    db.add(b); db.flush(); db.add(m.Notification(title="Baseline awaiting review",message=f"Baseline v{version} for astronaut #{aid} is ready for medical review."))
    audit(db,user,"CALCULATE","baseline",b.id,f"Based on five valid Earth RESTING readings"); db.commit()
    return baseline_dict(b)

def baseline_dict(b):
    return {"id":b.id,"astronaut_id":b.astronaut_id,"version":b.version,"status":b.status,"reading_count":b.reading_count,
      "avg_heart_rate":b.avg_heart_rate,"min_heart_rate":b.min_heart_rate,"max_heart_rate":b.max_heart_rate,"std_heart_rate":b.std_heart_rate,
      "avg_spo2":b.avg_spo2,"min_spo2":b.min_spo2,"max_spo2":b.max_spo2,"avg_systolic":b.avg_systolic,"avg_diastolic":b.avg_diastolic,
      "comments":b.comments,"created_at":b.created_at.isoformat()}

@app.get("/api/baselines")
def baselines(aid:int|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Baseline)
    if aid: q=q.filter_by(astronaut_id=aid)
    if user.role=="astronaut":
        a=db.query(m.Astronaut).filter_by(email=user.email).first()
        q=q.filter_by(astronaut_id=a.id if a else -1)
    return [baseline_dict(x) for x in q.order_by(m.Baseline.created_at.desc()).all()]

@app.post("/api/baselines/{bid}/review")
def review_baseline(bid:int,data:ReviewIn,db:Session=Depends(get_db),user=Depends(require("medical_officer","administrator"))):
    b=db.get(m.Baseline,bid)
    if not b: raise HTTPException(404,"Baseline not found")
    if b.status!="Pending": raise HTTPException(409,"Only pending baselines can be reviewed")
    if data.decision not in {"Approved","Rejected","More data requested"}: raise HTTPException(422,"Invalid decision")
    b.status=data.decision; b.comments=data.comments; b.reviewed_at=datetime.utcnow(); b.reviewer_id=user.id
    db.add(m.MedicalReview(subject_type="baseline",subject_id=bid,decision=data.decision,comments=data.comments,reviewer_id=user.id))
    audit(db,user,"REVIEW","baseline",bid,data.decision); db.commit()
    return {"message":f"Baseline {data.decision.lower()}"}

@app.get("/api/alerts")
def alerts(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Alert)
    if user.role=="astronaut":
        a=db.query(m.Astronaut).filter_by(email=user.email).first(); q=q.filter_by(astronaut_id=a.id if a else -1)
    return [alert_dict(x) for x in q.order_by(m.Alert.created_at.desc()).all()]

@app.post("/api/alerts/{alert_id}/action")
def alert_action(alert_id:int,data:AlertAction,db:Session=Depends(get_db),user=Depends(require("medical_officer","administrator"))):
    a=db.get(m.Alert,alert_id)
    if not a: raise HTTPException(404,"Alert not found")
    if data.status not in {"Acknowledged","Resolved","Open"}: raise HTTPException(422,"Invalid alert status")
    a.status=data.status
    if data.status=="Acknowledged": a.acknowledged_by=user.id
    db.add(m.MedicalReview(subject_type="alert",subject_id=alert_id,decision=data.status,comments=data.comments,reviewer_id=user.id))
    audit(db,user,"ALERT_"+data.status.upper(),"alert",alert_id,data.comments); db.commit()
    return {"message":"Alert updated"}

@app.get("/api/analytics")
def analytics(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Reading)
    if user.role=="astronaut":
        a=db.query(m.Astronaut).filter_by(email=user.email).first(); q=q.filter_by(astronaut_id=a.id if a else -1)
    rows=q.order_by(m.Reading.recorded_at).limit(1000).all()
    return {"count":len(rows),"labels":[x.recorded_at.strftime("%m-%d %H:%M") for x in rows],
      "heart_rate":[x.heart_rate for x in rows],"spo2":[x.spo2 for x in rows],
      "systolic":[x.systolic_bp for x in rows],"diastolic":[x.diastolic_bp for x in rows],
      "environment":[x.environment for x in rows]}

@app.get("/api/notifications")
def notifications(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Notification).filter((m.Notification.user_id==None)|(m.Notification.user_id==user.id))
    return [{"id":x.id,"title":x.title,"message":x.message,"read":x.read,"created_at":x.created_at.isoformat()} for x in q.order_by(m.Notification.created_at.desc()).limit(100).all()]

@app.post("/api/notifications/{nid}/read")
def mark_read(nid:int,db:Session=Depends(get_db),user=Depends(current_user)):
    n=db.get(m.Notification,nid)
    if not n or (n.user_id not in (None,user.id)): raise HTTPException(404,"Notification not found")
    n.read=True; db.commit(); return {"message":"Marked as read"}

@app.get("/api/admin/users")
def users(db:Session=Depends(get_db),user=Depends(require("administrator"))):
    return [{"id":x.id,"username":x.username,"email":x.email,"role":x.role,"active":x.active} for x in db.query(m.User).all()]

@app.post("/api/admin/users")
def create_user(data:UserCreate,db:Session=Depends(get_db),user=Depends(require("administrator"))):
    if data.role not in ROLES: raise HTTPException(422,"Unknown role")
    if db.query(m.User).filter((m.User.username==data.username)|(m.User.email==data.email)).first(): raise HTTPException(409,"User exists")
    x=m.User(username=data.username,email=data.email,password_hash=hash_password(data.password),role=data.role)
    db.add(x); db.flush(); audit(db,user,"CREATE","user",x.id); db.commit(); return {"id":x.id,"message":"User created"}

@app.get("/api/admin/audit")
def audit_logs(db:Session=Depends(get_db),user=Depends(require("administrator"))):
    return [{"id":x.id,"user_id":x.user_id,"action":x.action,"entity":x.entity,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at.isoformat()} for x in db.query(m.AuditLog).order_by(m.AuditLog.created_at.desc()).limit(300).all()]

@app.get("/api/reports/readings.csv")
def export_csv(astronaut_id:int|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(m.Reading)
    if user.role=="astronaut":
        a=db.query(m.Astronaut).filter_by(email=user.email).first(); q=q.filter_by(astronaut_id=a.id if a else -1)
    if astronaut_id: q=q.filter_by(astronaut_id=astronaut_id)
    out=io.StringIO(); w=csv.writer(out)
    w.writerow(["id","astronaut_id","mission_id","heart_rate","spo2","systolic_bp","diastolic_bp","activity","mission_phase","sensor_source","quality_status","environment","recorded_at"])
    for x in q.order_by(m.Reading.recorded_at).all(): w.writerow([x.id,x.astronaut_id,x.mission_id,x.heart_rate,x.spo2,x.systolic_bp,x.diastolic_bp,x.activity,x.mission_phase,x.sensor_source,x.quality_status,x.environment,x.recorded_at])
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=astra_health_readings.csv"})

@app.get("/api/reports/summary.pdf")
def export_pdf(db:Session=Depends(get_db),user=Depends(current_user)):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4); styles=getSampleStyleSheet()
    readings=db.query(m.Reading).count(); astronauts=db.query(m.Astronaut).count(); alerts_count=db.query(m.Alert).count()
    story=[Paragraph("ASTRA HEALTH — Research Summary",styles["Title"]),Paragraph(f"Generated: {datetime.utcnow():%Y-%m-%d %H:%M UTC}",styles["Normal"]),Spacer(1,16)]
    data=[["Metric","Database value"],["Astronauts",str(astronauts)],["Health readings",str(readings)],["Alerts",str(alerts_count)]]
    t=Table(data); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#142B4B")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.5,colors.grey),("PADDING",(0,0),(-1,-1),8)]))
    story += [t,Spacer(1,18),Paragraph("Research prototype disclaimer",styles["Heading2"]),Paragraph("This report contains records stored in the ASTRA HEALTH prototype. Simulated readings may be present. Statistical deviations are not diagnoses and must not be used as a substitute for professional medical judgement.",styles["BodyText"])]
    doc.build(story); buf.seek(0)
    return StreamingResponse(buf,media_type="application/pdf",headers={"Content-Disposition":"attachment; filename=astra_health_summary.pdf"})

@app.post("/api/sync")
def sync_readings(items:list[ReadingIn],db:Session=Depends(get_db),user=Depends(current_user)):
    results=[]
    for item in items:
        if item.sync_key and db.query(m.Reading).filter_by(sync_key=item.sync_key).first():
            results.append({"sync_key":item.sync_key,"status":"duplicate"}); continue
        if not db.get(m.Astronaut,item.astronaut_id):
            results.append({"sync_key":item.sync_key,"status":"failed","reason":"Unknown astronaut"}); continue
        x=m.Reading(**{**item.model_dump(),"recorded_at":item.recorded_at or datetime.utcnow()})
        db.add(x); db.flush(); evaluate_reading(db,user,x); audit(db,user,"SYNC","reading",x.id)
        results.append({"sync_key":item.sync_key,"status":"synced","id":x.id})
    db.commit()
    return {"results":results}

@app.get("/api/system/status")
def system_status(db:Session=Depends(get_db),user=Depends(require("administrator"))):
    return {"api":"online","database":"connected","database_type":"MySQL" if "mysql" in os.getenv("DATABASE_URL","") else "SQLite demo","version":app.version}
