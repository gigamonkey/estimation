import json
import random
import uuid
from datetime import datetime, timezone
from math import floor
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for

# TODO:
#
# Make results page that loads all the user results for a given
# question set and summarizes.
#
#


app = Flask(__name__)

# This is not very secret. That's okay as it is only used to encrpyt
# the client-side cookie data contining people's answers.
app.secret_key = b"&\x1a\r\t\x8d!&\xcd#\x1d\xd1\xcb[i\x18\x83"


quizdir = Path("quizes")
question_sets = Path("question-sets")


def load_words(filename):
    with open(filename) as f:
        return [w[:-1] for w in f]


words = load_words("words.txt")

#
# Jinja filters
#

app.jinja_env.globals.update(zip=zip)

@app.template_filter("number")
def format_number(n):
    if n == floor(n):
        return f"{int(n):,d}"
    else:
        int_part = floor(n)
        return f"{int_part:,d}.{round(100 * (n - int_part)):d}"


@app.template_filter("input_number")
def format_input_number(n):
    if n == floor(n):
        return f"{int(n):d}"
    else:
        int_part = floor(n)
        return f"{int_part:d}.{round(100 * (n - int_part)):d}"


@app.template_filter("percentage")
def format_percentage(n):
    return f"{round(100 * n)}%"


@app.template_filter("plural")
def plural(n, singular="", plural="s"):
    return singular if n == 1 else plural


#
# Routes
#


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/admin")
def admin():
    sets = sorted(p.stem for p in question_sets.glob("*.json"))
    quizes = sorted(p.name for p in quizdir.glob("*-*"))
    return render_template("admin.html", sets=sets, quizes=quizes)


@app.route("/new/<questions>")
def new(questions):
    name = create_quiz(questions)
    return render_template("new.html", url=url_for("start", name=name))


@app.route("/q/<name>")
def start(name):
    if "user_id" not in session:
        session["user_id"] = uuid.uuid4().hex
    session["name"] = name
    session.pop("answers", None)
    return render_template("start.html", url=url_for("question", name=name, n=1))


@app.route("/q/<name>/<int:n>", methods=["GET", "POST"])
def question(name, n):
    questions = load_questions(name)
    if "answers" not in session:
        session["answers"] = [None] * len(questions)

    answers = session["answers"]

    if request.method == "GET":
        low, high = current_answer(answers, n)
        return render_template(
            "question.html", questions=questions, n=n, low=low, high=high
        )
    else:
        name = session["name"]

        answers[n - 1] = {
            "low": float(request.form["low"]),
            "high": float(request.form["high"]),
        }
        session["answers"] = answers

        if n == len(questions):
            user_id = session["user_id"]
            results = generate_results(name, user_id, estimates(questions, answers))
            save_results(results)
            return redirect(url_for("done", name=name))
        else:
            return redirect(url_for("question", name=name, n=n + 1))


@app.route("/done/<name>")
def done(name):
    results = load_results(name, session["user_id"])
    return render_template("results.html", results=results)


@app.route("/s/<name>")
def summary(name):
    files = sorted(p for p in (quizdir / name).glob("*.json") if p.name != "quiz.json")
    combined = combined_estimates(files)
    extremes = generate_results(None, None, [combined_extremes(e) for e in combined])
    means = generate_results(None, None, [combined_mean(e) for e in combined])
    n = len(files)
    return render_template("summary.html", extremes=extremes, means=means, n=n)


#
# Utilities
#


def estimates(questions, answers):
    return [{**q, **a} for q, a in zip(questions, answers)]


def generate_results(name, user_id, estimates):

    timestamp = now()

    correct = 0
    too_low = 0
    too_high = 0

    for e in estimates:
        if e["a"] < e["low"]:
            too_high += 1
        elif e["a"] <= e["high"]:
            correct += 1
        else:
            too_low += 1

    fraction_correct = correct / len(estimates)

    return {
        "name": name,
        "user_id": user_id,
        "timestamp": timestamp,
        "fraction_correct": fraction_correct,
        "correct": correct,
        "too_low": too_low,
        "too_high": too_high,
        "estimates": estimates,
    }


def mean(xs):
    return sum(xs) / len(xs)


def combined_mean(e):
    return {"q": e["q"], "a": e["a"], "low": mean(e["low"]), "high": mean(e["high"])}


def combined_extremes(e):
    return {"q": e["q"], "a": e["a"], "low": min(e["low"]), "high": max(e["high"])}


def combined_estimates(results):
    combined = []
    for r in results:
        with open(r) as f:
            data = json.load(f)["estimates"]
            if not combined:
                combined = [first_combined(e) for e in data]
            else:
                for e, c in zip(data, combined):
                    c["low"].append(e["low"])
                    c["high"].append(e["high"])

    return combined


def first_combined(e):
    return {"q": e["q"], "a": e["a"], "low": [e["low"]], "high": [e["high"]]}


def current_answer(answers, n):
    a = answers[n - 1]
    if a is not None:
        return a["low"], a["high"]
    else:
        return None, None


def random_name(words, n=2):
    return "-".join(random.choice(words) for _ in range(n))


def now():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


#
# IO
#


def save_json(data, fp):
    print(f"Writing data t {fp}")
    json.dump(data, fp=fp, indent=2, ensure_ascii=False)


def question_set_file(name):
    return question_sets / f"{name}.json"


def quiz_file(name):
    return quizdir / name / "quiz.json"


def results_file(name, user_id):
    return quizdir / name / f"{user_id}.json"


def load_question_set(name):
    "Load a name set of questions from a json file."
    with open(question_sets / f"{name}.json") as f:
        return json.load(f)


def load_questions(name):
    "Load the questions for a named quiz."
    with open(quiz_file(name)) as f:
        quiz = json.load(f)
        return [{"q": q, "a": a} for q, a in quiz["questions"].items()]


def save_results(r):
    with open(results_file(r["name"], r["user_id"]), mode="w") as f:
        save_json(r, f)


def load_results(name, user_id):
    with open(results_file(name, user_id)) as f:
        return json.load(f)


def create_quiz(question_set):

    name = random_quiz(words)

    with open(quiz_file(name), mode="w") as f:
        data = {
            "timestamp": now(),
            "set": question_set,
            "questions": load_question_set(question_set),
        }
        save_json(data, f)

    return name


def random_quiz(words, n=2):
    done = False
    while not done:
        d = quizdir / random_name(words)
        try:
            print(f"Trying to make {d}")
            quizdir.mkdir(parents=True, exist_ok=True)
            d.mkdir(exist_ok=False)
            done = True
        except Exception as e:
            print(f"Exception {e}")
            pass  # Someone somehow created the same dir just before us!

    return d.name
