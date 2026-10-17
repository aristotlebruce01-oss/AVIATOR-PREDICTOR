from getpass import getpass
from app.main import DB,User,hashpw,code
d=DB()
try:
 if d.query(User).filter_by(role="super_admin").first():print("Super-admin already exists")
 else:
  name=input("Full name: ").strip();email=input("Email: ").strip().lower();pw=getpass("Password (8+ chars): ")
  u=User(full_name=name,email=email,password_hash=hashpw(pw),role="super_admin",referral_code=code("super_admin",d),commission_rate=0);d.add(u);d.commit();print("Created super-admin referral code:",u.referral_code)
finally:d.close()
