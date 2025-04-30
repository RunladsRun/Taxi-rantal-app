# app/models.py
from . import db

# ---- Driver model ----
class Driver(db.Model):
    __tablename__ = 'driver'

    name = db.Column(db.String, primary_key=True)
    address = db.Column(db.String, nullable=False)

