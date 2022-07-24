from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort

from jinja2 import Environment, PackageLoader, select_autoescape
env = Environment(
   keep_trailing_newline=True 
)
import os
app = Flask(__name__)
app.secret_key = b'ahcqweiu55pjds6it7y'

@app.route("/")
def index():
    return render_template("website.html")

@app.route("/cow", methods=["GET"])
def cow():
    return render_template("cow.html")

@app.route("/cow", methods=["POST"])
def process_text():
    cowtext = ""
    user_input = request.form["input_text"]
    os.system(f"cowsay {user_input} > out.txt")
    try:
        with open("out.txt", "r") as f:
            cowtext = f.read()
        os.remove("out.txt")
    except:
        message = "invalid input passed to cowsay"
        return render_template("cow.html", cowtext = "", message=message)
    
    return render_template("cow.html", cowtext = cowtext)

@app.route("/sent")
def message_sent():
    return render_template("sent.html")
