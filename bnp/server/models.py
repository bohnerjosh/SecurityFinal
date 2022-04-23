from server.siteappserver import db

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(16), unique=True, nullable=False)
    password = db.Column(db.String(16), unique=False, nullable=False)
    email = db.Column(db.String(20), unique=False, nullable=False)
    photofn = db.Column(db.String(80), unique=False, nullable=True)
    diaries = db.relationship('PrivateDiary', backref='profile', lazy=True)

    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'email': self.email,
            'photofn': self.photofn,
        }

    def __repr__(self):
        return '<Profile id=%r>' % self.id

class PrivateDiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(144), unique=False, nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'), nullable=False)
    name = db.Column(db.String(32), unique=False, nullable=False)
    date = db.Column(db.String(10), unique=False, nullable=False)

    def serialize(self):
        return {
            'id': self.id,
            'content': self.content,
            'profile': self.profile.serialize(),
            'name': self.name,
            'date': self.date
        }
