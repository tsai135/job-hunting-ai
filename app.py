from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/match")
def match():
    jobs = [
        {
            "title": "Software Engineer",
            "company": "Google",
            "score": 92
        },
        {
            "title": "Python Developer",
            "company": "Microsoft",
            "score": 85
        }
    ]

    return render_template("results.html", jobs=jobs)


if __name__ == "__main__":
    app.run(debug=True)