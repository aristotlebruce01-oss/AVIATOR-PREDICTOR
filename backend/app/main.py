import os,secrets,string,shutil
from datetime import datetime,timedelta,date
from typing import Optional
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Form,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import jwt,JWTError
from passlib.context import CryptContext
from pydantic import BaseModel,EmailStr
from sqlalchemy import create_engine,Column,Integer,String,Float,DateTime,Boolean,ForeignKey, text
from sqlalchemy.orm import declarative_base,sessionmaker,Session
from dotenv import load_dotenv
load_dotenv()
SECRET=os.getenv("JWT_SECRET","DEV-ONLY-change-before-deploy"); ALG="HS256"; UPLOAD=os.getenv("UPLOAD_DIR","uploads"); os.makedirs(UPLOAD,exist_ok=True)
URL=os.getenv("DATABASE_URL","sqlite:///./aviator.db"); engine=create_engine(URL,connect_args={"check_same_thread":False} if URL.startswith("sqlite") else {})
DB=sessionmaker(bind=engine,autoflush=False,autocommit=False); Base=declarative_base(); pwd=CryptContext(schemes=["bcrypt"],deprecated="auto"); oauth=OAuth2PasswordBearer(tokenUrl="/auth/login")
PACKAGES={"BASIC":{"amount":300,"predictions":2},"STANDARD":{"amount":500,"predictions":4},"ADVANCED":{"amount":700,"predictions":6},"PREMIUM":{"amount":1000,"predictions":8},"ULTIMATE":{"amount":1500,"predictions":10},"INFINITE":{"amount":2000,"predictions":None}}
PAYMENT_OPTIONS={"MTN MoMo":{"number":"0558559878","name":"Godfred Fosu Gyan"},"Telecel Cash":{"number":"0509623244","name":"Godfred Fosu Gyan"},"Bank Transfer":{"bank":"GCB","number":"1011103552151","name":"Godfred Fosu Gyan"}}
class User(Base):
 __tablename__="users"
 id=Column(Integer,primary_key=True); email=Column(String,unique=True,index=True,nullable=True); phone=Column(String,unique=True,index=True,nullable=True); password_hash=Column(String,nullable=False); full_name=Column(String,nullable=False); role=Column(String,default="user",nullable=False); referred_by_code=Column(String,index=True); referral_code=Column(String,unique=True,index=True); commission_rate=Column(Float,default=.70); created_at=Column(DateTime,default=datetime.utcnow); active=Column(Boolean,default=True)
class PaymentOption(Base):
 __tablename__="payment_options"
 method=Column(String,primary_key=True); number=Column(String,nullable=False); name=Column(String,nullable=False); bank=Column(String,nullable=True)
class Payment(Base):
 __tablename__="payments"
 id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey("users.id"),index=True); package_name=Column(String); amount=Column(Float); predictions=Column(Integer,nullable=True); payment_method=Column(String); sender_name=Column(String); sender_phone=Column(String); transaction_ref=Column(String,index=True); proof_path=Column(String,nullable=True); status=Column(String,default="pending",index=True); created_at=Column(DateTime,default=datetime.utcnow,index=True); reviewed_at=Column(DateTime,nullable=True); reviewed_by=Column(Integer,nullable=True); archived_at=Column(DateTime,nullable=True); predictions_used=Column(Integer,default=0,nullable=False)
Base.metadata.create_all(engine)
# Add the usage counter safely for existing SQLite/PostgreSQL databases created by older app versions.
with engine.begin() as conn:
 try:
  cols=[row[1] for row in conn.execute(text("PRAGMA table_info(payments)")).fetchall()] if URL.startswith("sqlite") else [row[0] for row in conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='payments'")).fetchall()]
  if "predictions_used" not in cols:
   conn.execute(text("ALTER TABLE payments ADD COLUMN predictions_used INTEGER NOT NULL DEFAULT 0"))
 except Exception:
  pass
# Seed default manual payment details only when a method has no saved configuration.
with DB() as seed_db:
 for method, values in {"MTN MoMo":{"number":"0558559878","name":"Godfred Fosu Gyan","bank":None},"Telecel Cash":{"number":"0509623244","name":"Godfred Fosu Gyan","bank":None},"Bank Transfer":{"number":"1011103552151","name":"Godfred Fosu Gyan","bank":"GCB"}}.items():
  if not seed_db.query(PaymentOption).filter_by(method=method).first(): seed_db.add(PaymentOption(method=method,**values))
 seed_db.commit()
app=FastAPI(title="Aviator Predictor API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv(
            "FRONTEND_ORIGIN",
            "https://aviator-predictor-two-pied.vercel.app"
        ),
        "http://localhost:5173",
        "http://172.20.10.4:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def db_dep():
 d=DB()
 try: yield d
 finally:d.close()
def token_for(u):return jwt.encode({"sub":str(u.id),"exp":datetime.utcnow()+timedelta(hours=12)},SECRET,algorithm=ALG)
def auth(token:str=Depends(oauth),d:Session=Depends(db_dep)):
 try: uid=int(jwt.decode(token,SECRET,algorithms=[ALG])["sub"])
 except Exception:raise HTTPException(401,"Invalid or expired token")
 u=d.query(User).filter_by(id=uid,active=True).first()
 if not u:raise HTTPException(401,"Account unavailable")
 return u
def roles(*allowed):
 def check(u:User=Depends(auth)):
  if u.role not in allowed:raise HTTPException(403,"Forbidden for this role")
  return u
 return check
def hashpw(p):
 if len(p)<6:raise HTTPException(400,"Password must be at least 6 characters")
 return pwd.hash(p[:72])
def code(role,d):
 for _ in range(50):
  c=''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(8))
  if not d.query(User).filter_by(referral_code=c).first():return c
 raise HTTPException(500,"Referral code generation failed")
def ud(u):return {"id":u.id,"email":u.email,"phone":u.phone,"full_name":u.full_name,"role":u.role,"referral_code":u.referral_code,"referred_by_code":u.referred_by_code,"commission_rate":u.commission_rate,"created_at":u.created_at.isoformat()}
def pd(p,d):
 u=d.query(User).filter_by(id=p.user_id).first()
 return {"id":p.id,"user_name":u.full_name if u else "Unknown","email":u.email if u else None,"phone":u.phone if u else None,"package_name":p.package_name,"amount":p.amount,"predictions":p.predictions,"payment_method":p.payment_method,"sender_name":p.sender_name,"sender_phone":p.sender_phone,"transaction_ref":p.transaction_ref,"proof_available":bool(p.proof_path),"status":p.status,"created_at":p.created_at.strftime("%Y-%m-%d %I:%M %p"),"reviewed_at":p.reviewed_at.isoformat() if p.reviewed_at else None}
class Signup(BaseModel):
 full_name:str; email:Optional[EmailStr]=None; phone:Optional[str]=None; password:str; referral_code:Optional[str]=None
class Login(BaseModel):login:str;password:str
class Staff(BaseModel):
 full_name:str; email:Optional[EmailStr]=None; phone:Optional[str]=None; password:str; role:str
@app.get("/")
def root():return {"ok":True,"service":"Aviator Predictor API"}
def payment_options_data(d:Session):
 rows=d.query(PaymentOption).all()
 if not rows:return PAYMENT_OPTIONS
 return {r.method:{"number":r.number,"name":r.name,**({"bank":r.bank} if r.bank else {})} for r in rows}
@app.get("/public/packages")
def packages(d:Session=Depends(db_dep)):return {"packages":PACKAGES,"payment_options":payment_options_data(d)}
class PaymentOptionUpdate(BaseModel):
 method:str; number:str; name:str; bank:Optional[str]=None
@app.put("/admin/payment-options")
def update_payment_options(items:list[PaymentOptionUpdate],u:User=Depends(roles("super_admin")),d:Session=Depends(db_dep)):
 allowed={"MTN MoMo","Telecel Cash","Bank Transfer"}
 seen=set()
 for item in items:
  if item.method not in allowed or item.method in seen: raise HTTPException(400,"Invalid or duplicate payment method")
  if not item.number.strip() or not item.name.strip(): raise HTTPException(400,"Account number and account name are required")
  if item.method=="Bank Transfer" and not (item.bank or "").strip(): raise HTTPException(400,"Bank name is required for Bank Transfer")
  seen.add(item.method)
 if seen!=allowed: raise HTTPException(400,"All manual payment methods must be included")
 for item in items:
  row=d.query(PaymentOption).filter_by(method=item.method).first()
  if not row: row=PaymentOption(method=item.method);d.add(row)
  row.number=item.number.strip();row.name=item.name.strip();row.bank=(item.bank or "").strip() or None
 d.commit()
 return {"payment_options":payment_options_data(d),"message":"Manual payment details updated successfully."}
@app.on_event("startup")
def seed_superadmin():
    try:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        admin = db.query(User).filter(User.role == "super_admin").first()
        if not admin:
            hashed_password = hashpw("Godfred10"[:72])
            super_admin_user = User(
                username="superadmin",
                email="aristotlebruce01@gmail.com",
                phone="0509623244",
                full_name="Godfred Fosu Gyan",
                password_hash=hashed_password,
                role="super_admin",
                active=True
            )
            db.add(super_admin_user)
            db.commit()
            print("SuperAdmin account seeded successfully!")
        db.close()
    except Exception as e:
        print(f"Startup seeding error: {e}")
@app.post("/auth/signup")
def signup(b:Signup,d:Session=Depends(db_dep)):
 if not b.email and not b.phone:raise HTTPException(400,"Email or phone is required")
 if b.email and d.query(User).filter_by(email=str(b.email).lower()).first():raise HTTPException(409,"Email already registered")
 if b.phone and d.query(User).filter_by(phone=b.phone).first():raise HTTPException(409,"Phone already registered")
 ref=(b.referral_code or "").strip().upper() or None
 if ref and not d.query(User).filter(User.referral_code==ref,User.role.in_(["super_admin","admin","sub_admin"])).first():raise HTTPException(400,"Invalid referral code")
 u=User(full_name=b.full_name,email=str(b.email).lower() if b.email else None,phone=b.phone,password_hash=hashpw(b.password),role="user",referred_by_code=ref)
 d.add(u);d.commit();d.refresh(u);return {"user":ud(u),"access_token":token_for(u)}
@app.post("/auth/login")
def login(b:Login,d:Session=Depends(db_dep)):
 u=d.query(User).filter((User.email==b.login.lower())|(User.phone==b.login)).first()
 if not u or not pwd.verify(b.password[:72], u.password_hash) or not u.active: raise HTTPException(401, "Invalid login")
 return {"user":ud(u),"access_token":token_for(u)}
@app.get("/auth/me")
def me(u:User=Depends(auth)):return ud(u)
@app.post("/payments/submit")
async def submit(package_name:str=Form(...),payment_method:str=Form(...),sender_name:str=Form(...),sender_phone:str=Form(...),transaction_ref:str=Form(...),proof:Optional[UploadFile]=File(None),u:User=Depends(auth),d:Session=Depends(db_dep)):
 name=package_name.upper()
 if name not in PACKAGES or payment_method not in payment_options_data(d):raise HTTPException(400,"Invalid package or payment method")
 if not sender_name.strip() or not sender_phone.strip() or not transaction_ref.strip():raise HTTPException(400,"Sender name, phone and transaction reference required")
 path=None
 if proof and proof.filename:
  if proof.content_type not in ["image/jpeg","image/png","image/webp"]:raise HTTPException(400,"Proof must be JPG, PNG or WEBP")
  path=f"{u.id}_{secrets.token_hex(12)}"
  with open(os.path.join(UPLOAD,path),"wb") as f:shutil.copyfileobj(proof.file,f)
 pkg=PACKAGES[name];p=Payment(user_id=u.id,package_name=name,amount=pkg["amount"],predictions=pkg["predictions"],payment_method=payment_method,sender_name=sender_name.strip(),sender_phone=sender_phone.strip(),transaction_ref=transaction_ref.strip(),proof_path=path)
 d.add(p);d.commit();d.refresh(p);return {"payment":pd(p,d),"message":"Submitted for review. Access opens only after administrator approval."}
@app.get("/payments/mine")
def mine(u:User=Depends(auth),d:Session=Depends(db_dep)):return [pd(p,d) for p in d.query(Payment).filter_by(user_id=u.id).order_by(Payment.created_at.desc()).all()]
def current_package(u:User,d:Session):
 if u.role in ["super_admin","admin","sub_admin"]:
  return None
 return d.query(Payment).filter_by(user_id=u.id,status="approved",archived_at=None).order_by(Payment.reviewed_at.desc(),Payment.id.desc()).first()
@app.get("/predictor/access")
def access(u:User=Depends(auth),d:Session=Depends(db_dep)):
 if u.role in ["super_admin","admin","sub_admin"]:
  return {"allowed":True,"package":"STAFF ACCESS","predictions":None,"predictions_used":0,"remaining":None,"exhausted":False,"free_access":True}
 p=current_package(u,d)
 if not p:
  approved=d.query(Payment).filter_by(user_id=u.id,status="approved",archived_at=None).order_by(Payment.id.desc()).first()
  exhausted=bool(approved and approved.predictions is not None and (approved.predictions_used or 0)>=approved.predictions)
  return {"allowed":False,"package":approved.package_name if approved else None,"predictions":approved.predictions if approved else 0,"predictions_used":approved.predictions_used if approved else 0,"remaining":0,"exhausted":exhausted,"free_access":False}
 remaining=None if p.predictions is None else max(0,p.predictions-(p.predictions_used or 0))
 exhausted=remaining==0 if remaining is not None else False
 return {"allowed":not exhausted,"package":p.package_name,"predictions":p.predictions,"predictions_used":p.predictions_used or 0,"remaining":remaining,"exhausted":exhausted,"free_access":False}
@app.get("/predictor/demo")
def demo(u:User=Depends(auth),d:Session=Depends(db_dep)):
 p=None
 if u.role not in ["super_admin","admin","sub_admin"]:
  p=current_package(u,d)
  if not p: raise HTTPException(403,{"code":"PACKAGE_EXHAUSTED","message":"You’ve exhausted your prediction package. Purchase another one."} if d.query(Payment).filter_by(user_id=u.id,status="approved",archived_at=None).first() else "Approved package required")
  if p.predictions is not None and (p.predictions_used or 0)>=p.predictions:
   raise HTTPException(403,{"code":"PACKAGE_EXHAUSTED","message":"You’ve exhausted your prediction package. Purchase another one."})
  p.predictions_used=(p.predictions_used or 0)+1
  d.commit()
 # Generate one standalone multiplier outcome across small, medium, and very high values.
 bucket=secrets.randbelow(100)
 if bucket < 30:
  target=(100+secrets.randbelow(901))/100
 elif bucket < 75:
  target=(1001+secrets.randbelow(12000))/100
 else:
  target=(13001+secrets.randbelow(77800))/100
 return {"target_multiplier":round(target,2),"predictions_remaining":None if p is None or p.predictions is None else max(0,p.predictions-p.predictions_used),"package_name":p.package_name if p else "STAFF ACCESS"}
@app.get("/admin/payments")
def payments(status:Optional[str]=None,u:User=Depends(roles("admin","super_admin")),d:Session=Depends(db_dep)):
 q=d.query(Payment).filter(Payment.archived_at==None)
 if status in ["pending","approved","rejected"]:q=q.filter_by(status=status)
 return [pd(p,d) for p in q.order_by(Payment.created_at.desc()).all()]
@app.post("/admin/payments/{pid}/review")
def review(pid:int,decision:str,u:User=Depends(roles("admin","super_admin")),d:Session=Depends(db_dep)):
 p=d.query(Payment).filter_by(id=pid,archived_at=None).first()
 if not p:raise HTTPException(404,"Payment not found")
 if decision not in ["approve","reject"] or p.status!="pending":raise HTTPException(400,"Invalid decision or already reviewed")
 p.status="approved" if decision=="approve" else "rejected";p.reviewed_at=datetime.utcnow();p.reviewed_by=u.id;d.commit();return pd(p,d)
@app.get("/admin/staff/manage")
def staff_list(u:User=Depends(roles("super_admin")),d:Session=Depends(db_dep)):return [ud(x) for x in d.query(User).filter(User.role.in_(["admin","sub_admin"])).all()]
@app.post("/admin/users/create-staff")
def create_staff(b:Staff,u:User=Depends(roles("admin","super_admin")),d:Session=Depends(db_dep)):
 if b.role not in ["admin","sub_admin"]:raise HTTPException(400,"Role must be admin or sub_admin")
 if b.role=="admin" and u.role!="super_admin":raise HTTPException(403,"Only super-admin can create admins")
 if not b.email and not b.phone:raise HTTPException(400,"Email or phone required")
 if b.email and d.query(User).filter_by(email=str(b.email).lower()).first():raise HTTPException(409,"Email exists")
 if b.phone and d.query(User).filter_by(phone=b.phone).first():raise HTTPException(409,"Phone exists")
 x=User(full_name=b.full_name,email=str(b.email).lower() if b.email else None,phone=b.phone,password_hash=hashpw(b.password),role=b.role,referral_code=code(b.role,d),commission_rate=.70 if b.role=="sub_admin" else 1.0)
 d.add(x);d.commit();d.refresh(x);return ud(x)
@app.delete("/admin/staff/manage/{uid}")
def delete_staff(uid:int,u:User=Depends(roles("admin","super_admin")),d:Session=Depends(db_dep)):
 x=d.query(User).filter_by(id=uid).first()
 if not x:raise HTTPException(404,"Not found")
 if x.role=="super_admin":raise HTTPException(403,"Cannot delete super-admin")
 if u.role=="admin" and x.role!="sub_admin":raise HTTPException(403,"Admins may only deactivate sub-admins")
 x.active=False;d.commit();return {"ok":True}
@app.get("/admin/users")
def users(u:User=Depends(roles("admin","super_admin")),d:Session=Depends(db_dep)):return [ud(x) for x in d.query(User).filter_by(role="user").all()]
@app.get("/admin/reports/financial")
def report(u:User=Depends(roles("super_admin")),d:Session=Depends(db_dep)):
 ps=d.query(Payment).filter_by(status="approved",archived_at=None).all()
 return {"approved_total":sum(p.amount for p in ps),"approved_count":len(ps),"pending_count":d.query(Payment).filter_by(status="pending").count()}
@app.get("/dashboard/referrals")
def referrals(u:User=Depends(roles("super_admin","admin","sub_admin")),d:Session=Depends(db_dep)):
 users=d.query(User).filter_by(referred_by_code=u.referral_code).all() if u.referral_code else [];ledger=[];today_total=all_total=0;today=date.today()
 for x in users:
  for p in d.query(Payment).filter_by(user_id=x.id,status="approved",archived_at=None).all():
   commission=round(p.amount*(.70 if u.role=="sub_admin" else 1.0),2);when=p.reviewed_at or p.created_at;all_total+=commission
   if when.date()==today:today_total+=commission
   ledger.append({"date_time":when.strftime("%Y-%m-%d %I:%M %p"),"user_name":x.full_name,"email":x.email,"phone":x.phone,"package":p.package_name,"deposit_amount":p.amount,"commission":commission})
 return {"referral_code":u.referral_code,"today_commission":today_total,"all_time_commission":all_total,"users":[{"name":x.full_name,"email":x.email,"phone":x.phone} for x in users],"ledger":sorted(ledger,key=lambda x:x["date_time"],reverse=True)}
@app.get("/admin/matches")
def matches(u:User=Depends(roles("admin","super_admin","sub_admin"))):return {"message":"Match engine integration placeholder"}
@app.delete("/admin/package-amount/clear-older")
def archive(days:int=Query(90,ge=1,le=3650),before:Optional[date]=None,u:User=Depends(roles("super_admin")),d:Session=Depends(db_dep)):
 cutoff=datetime.combine(before,datetime.min.time()) if before else datetime.utcnow()-timedelta(days=days);rows=d.query(Payment).filter(Payment.created_at<cutoff,Payment.archived_at==None).all()
 for p in rows:p.archived_at=datetime.utcnow()
 d.commit();return {"archived_count":len(rows),"cutoff":cutoff.isoformat(),"soft_archive":True}
