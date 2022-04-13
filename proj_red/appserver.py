from flask import Flask, render_template, request, session, redirect, url_for, jsonify, abort

app = Flask(__name__)
app.secret_key = b'ahcqweiu55pjds6it7y'

@app.route("/")
def index():
    return render_template("website.html")

@app.route("/cow")
def cow():
    return render_template("cow.html")
