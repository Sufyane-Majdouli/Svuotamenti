from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional

class FTPSettingsForm(FlaskForm):
    """Form for FTP connection settings"""
    host = StringField('FTP Host', validators=[DataRequired()])
    port = IntegerField('FTP Port', validators=[DataRequired(), NumberRange(min=1, max=65535)], default=21)
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Optional()])
    submit = SubmitField('Connect')

class UploadForm(FlaskForm):
    """Form for uploading CSV files"""
    file = FileField('CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload') 