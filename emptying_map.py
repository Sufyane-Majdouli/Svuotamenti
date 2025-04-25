#!/usr/bin/env python

"""
Emptying Map Web Application
This script launches the Svuotamenti web application
"""

from app import app

if __name__ == "__main__":
    app.run(debug=True) 