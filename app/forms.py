from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import MultipleFileField, SubmitField
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired, NumberRange, Optional

class FTPSettingsForm(FlaskForm):
    """Form for FTP connection settings"""
    host = StringField('FTP Host', validators=[DataRequired()])
    port = IntegerField('FTP Port', validators=[DataRequired(), NumberRange(min=1, max=65535)], default=21)
    username = StringField('Username', validators=[DataRequired()], render_kw={"autocomplete": "username"})
    password = PasswordField('Password', validators=[Optional()], render_kw={"autocomplete": "current-password"})
    submit = SubmitField('Connect')

class UploadForm(FlaskForm):
    """Form for uploading CSV files"""
    files = MultipleFileField('CSV Files', validators=[
        DataRequired(message='Please select at least one CSV file.'),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Upload Files') 