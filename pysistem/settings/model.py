# -*- coding: utf-8 -*-

"""Database setting storage backend"""

from pysistem import db

SETTING_INT = 1
SETTING_STRING = 2
SETTING_BOOL = 3
SETTING_EMPTY = 0

DEFAULT = {
    "allow_signup": True,
    "allow_guest_view": True,
    "scoreboard_cache_timeout": 60
}

cached = {}

class Setting(db.Model):
    """A global server setting

    Fields:
    name -- unique setting name
    type -- setting type: SETTING_INT, SETTING_STRING or SETTING_BOOL
    value_int -- setting value if type in [SETTING_INT, SETTING_BOOL], None otherwise
    value_string -- setting value if type == SETTING_STRING, None otherwise
    """

    name = db.Column(db.String(80), primary_key=True)
    type = db.Column(db.Integer)
    value_int = db.Column(db.Integer)
    value_string = db.Column(db.Text)

    def __init__(self, name, value=0):
        self.name = name
        if isinstance(value, int):
            self.type = SETTING_INT
            self.value_int = value
        elif isinstance(value, bool):
            self.type = SETTING_BOOL
            self.value_int = int(value)
        elif isinstance(value, str):
            self.type = SETTING_STRING
            self.value_string = value
        else:
            self.type = SETTING_EMPTY

    def __repr__(self):
        return '<Setting %r=%r>' % (self.name, self.val())

    def val(self):
        """Get self value with auto-conversion"""
        if self.type == SETTING_INT:
            return self.value_int
        if self.type == SETTING_STRING:
            return self.value_string
        if self.type == SETTING_BOOL:
            return bool(self.value_int)
        return None

    @staticmethod
    def get(name, default=None):
        """Global function. Get value by name"""
        if cached.get(name):
            return cached.get(name)
        default = DEFAULT.get(name) or default
        setting = Setting.query.get(name)
        if setting is None:
            return default
        value = setting.val()
        if value is None:
            return default
        return value

    @staticmethod
    def set(name, value):
        """Global function. Set value"""
        cached[name] = value
        setting = Setting.query.get(name)
        if setting:
            if isinstance(value, int):
                setting.type = SETTING_INT
                setting.value_int = value
            elif isinstance(value, str):
                setting.type = SETTING_STRING
                setting.value_string = value
            elif isinstance(value, bool):
                setting.type = SETTING_BOOL
                setting.value_int = int(value)
            else:
                setting.type = SETTING_EMPTY
        else:
            setting = Setting(name, value)
        db.session.add(setting)
        db.session.commit()
