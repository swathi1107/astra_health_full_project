from app.database import Base, engine, SessionLocal
from app.models import User, Astronaut, Mission
from app.security import hash_password
Base.metadata.create_all(engine)
db=SessionLocal()
accounts=[
 ("admin","admin@astra.local","AdminDemo123!","administrator"),
 ("medical","medical@astra.local","MedicalDemo123!","medical_officer"),
 ("research","research@astra.local","ResearchDemo123!","researcher"),
 ("astro","astro@astra.local","AstronautDemo123!","astronaut")]
for username,email,pw,role in accounts:
    if not db.query(User).filter_by(username=username).first():
        db.add(User(username=username,email=email,password_hash=hash_password(pw),role=role))
if not db.query(Astronaut).filter_by(astronaut_code="AST-001").first():
    db.add(Astronaut(astronaut_code="AST-001",full_name="Demo Astronaut",email="astro@astra.local",status="Active"))
if not db.query(Mission).filter_by(name="ORBIT-01").first():
    from datetime import date
    db.add(Mission(name="ORBIT-01",description="Demonstration mission record",status="Active",phase="In-flight",start_date=date.today()))
db.commit(); db.close()
print("Demo data ready.")
print("admin / AdminDemo123! | medical / MedicalDemo123! | research / ResearchDemo123! | astro / AstronautDemo123!")
