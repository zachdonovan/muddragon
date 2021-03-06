from sqlalchemy import func
from bootstrap import get_db

db = get_db()

class DnfBase(db.Model):
    __abstract__ = True

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

friendships = db.Table("friendships",
                       db.Column('friend_social_id',
                                 db.String(32),
                                 db.ForeignKey('player.social_id'),
                                 primary_key=True),
                       db.Column('friend_of_social_id',
                                 db.String(32),
                                 db.ForeignKey('player.social_id'),
                                 primary_key=True))


class Score(DnfBase):
    player_social_id = db.Column(db.String(32), db.ForeignKey(
        'player.social_id'), primary_key=True)
    puzzle_id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    stars = db.Column(db.Integer, nullable=False)

    def __init__(self, player_social_id, puzzle_id, score, stars):
        self.player_social_id = player_social_id
        self.puzzle_id = puzzle_id
        self.score = score
        self.stars = stars

    @staticmethod
    def maybe_update_score(props):
        score = db.session.query(Score).filter(
            Score.player_social_id == props['player_social_id'],
            Score.puzzle_id == props['puzzle_id']).first()
        if not score:
            score = Score(**props)
            db.session.add(score)
        else:
            score.stars = max(props['stars'], score.stars)
            score.score = max(props['score'], score.score)


class Player(DnfBase):
    social_id = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(128))
    email = db.Column(db.String(128))

    friends = db.relationship("Player",
                              secondary=friendships,
                              primaryjoin=social_id ==
                              friendships.c.friend_social_id,
                              secondaryjoin=social_id ==
                              friendships.c.friend_of_social_id,
                              backref="friend_of")

    puzzle_data = db.relationship("Score", backref='player')

    def __init__(self,
                 social_id,
                 name=None,
                 email=None):
        self.social_id = social_id
        self.name = name or ""
        self.email = email or ""

    def __repr__(self):
        return "<Player {}, {}, {}>".format(
            self.social_id, self.name, self.email)

    @staticmethod
    def get_or_create(props):
        player = Player.query.filter(
            Player.social_id == props['social_id']).first()
        if not player:
            player = Player(**props)
            db.session.add(player)

        return player

    def add_friendship(self, friend):
        self.friends.append(friend)
        friend.friends.append(self)

    def compute_puzzle_data(self):
        scores = db.session.query(Score).filter(
            Score.player_social_id == self.social_id).all()
        data = {'scores': [], 'puzzles': [], 'stars': []}
        for score in scores:
            data['puzzles'].append(score.puzzle_id)
            data['scores'].append(score.score)
            data['stars'].append(score.stars)

        return data

    def compute_friends_data(self):
        return [{'social_id': _.social_id,
                 'puzzle_data': _.compute_puzzle_data()
                 } for _ in self.friends]

    def compute_high_scores_data(self):
        puzzles = db.session.query(Score.puzzle_id).filter(
            Score.player_social_id == self.social_id).all()
        hi_scores = db.session.query(Score.puzzle_id,
                                     func.max(Score.score),
                                     Score.player_social_id).join(
            Player).filter(
            Player.social_id.in_([self.social_id] + [_.social_id for
                                                     _ in
                                                     self.friends])).filter(
            Score.puzzle_id.in_([_.puzzle_id for _ in puzzles])).group_by(Score.puzzle_id)
        data = {'puzzles': [], 'leaders': [], 'scores': []}
        for puzzle_id, high_score, player_social_id in hi_scores:
            data['puzzles'].append(puzzle_id)
            data['leaders'].append(player_social_id)
            data['scores'].append(high_score)

        return data


db.create_all()
