import sqlalchemy as sa


class TZAwareDateTime(sa.DateTime):
    def __init__(self):
        super().__init__(timezone=True)
