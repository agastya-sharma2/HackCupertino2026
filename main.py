from flask import Flask, redirect, url_for, render_template, flash, request

app = Flask(__name__)
app.secret_key = "2-fat-2-fit"

@app.route("/strech", methods=["GET", "POST"])
def stretchPage():
    return render_template("stretches.html", stretch="[placeholder]", time="[placeholdeR]")

@app.route("/food", methods=["GET", "POST"])
def foodPage():
    return render_template("food.html")

@app.route("/type", methods=["GET", "POST"])
def typePage():
    return render_template("type.html")


if __name__ == "__main__":
    app.run()